import logging
import os
import re
import hashlib
import math
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from src.video_crud_service.database import SessionLocal, init_db
from src.video_crud_service.models import (
    Video,
    VideoTranscript,
    VideoSummary,
    VideoTag,
    TagTaxonomy,
    TagAlias,
)
from src.video_crud_service.videos import serialize_video
from src.communication_service.models import Notification
from src.dashboard_service.models import SearchHistory, WatchHistory, Subscription, User
from src.dashboard_service.tag_taxonomy import TAG_TAXONOMY_SEED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
COMMUNICATION_API_BASE_URL = os.getenv("COMMUNICATION_API_BASE_URL", "").strip().rstrip("/")
INTELLIGENCE_API_BASE_URL = os.getenv("INTELLIGENCE_API_BASE_URL", "").strip().rstrip("/")
SUMMARY_WAIT_TRANSCRIPT_SECONDS = int(os.getenv("SUMMARY_WAIT_TRANSCRIPT_SECONDS", "12"))
SUMMARY_WAIT_TRANSCRIPT_POLL_SECONDS = float(os.getenv("SUMMARY_WAIT_TRANSCRIPT_POLL_SECONDS", "1.0"))
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "2000"))
TAG_LOW_CONFIDENCE_THRESHOLD = float(os.getenv("TAG_LOW_CONFIDENCE_THRESHOLD", "0.34"))

app = FastAPI(title="Dashboard Service")

_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://vcm-52418.vm.duke.edu:5173",
    "http://vcm-52527.vm.duke.edu:5173",
]
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def _send_subscription_notifications(subscriber_user_id: str, channel_user_id: str) -> None:
    if not COMMUNICATION_API_BASE_URL:
        return

    payloads = [
        {
            "type": "subscription",
            "recipient_user_ids": [subscriber_user_id],
            "title": "Subscription confirmed",
            "message": f"You subscribed to channel {channel_user_id}.",
            "actor_user_id": channel_user_id,
            "channel_id": channel_user_id,
            "video_id": None,
        },
        {
            "type": "subscription",
            "recipient_user_ids": [channel_user_id],
            "title": "New subscriber",
            "message": f"User {subscriber_user_id} subscribed to your channel.",
            "actor_user_id": subscriber_user_id,
            "channel_id": channel_user_id,
            "video_id": None,
        },
    ]

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            for payload in payloads:
                response = await client.post(
                    f"{COMMUNICATION_API_BASE_URL}/comm/notifications",
                    json=payload,
                )
                response.raise_for_status()
    except Exception:
        # Notification is best-effort. Core subscription flow should still succeed.
        logger.exception(
            "Failed to send subscription notifications subscriber=%s channel=%s",
            subscriber_user_id,
            channel_user_id,
        )


class SummarizeRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    subtitle_text: str | None = Field(default=None, min_length=1, max_length=20000)
    max_sentences: int = Field(default=3, ge=1, le=5)
    force_refresh: bool = Field(default=False)


class TaggingRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    max_tags: int = Field(default=5, ge=1, le=10)


def _clip_text(value: str, max_length: int) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 3].rstrip()}..."


def _build_summary_source_text(
    *,
    db: Session,
    video: Video,
    subtitle_text: str | None,
) -> tuple[str, str]:
    if subtitle_text and subtitle_text.strip():
        return subtitle_text.strip(), "subtitle_text"

    transcript_row = db.query(VideoTranscript).filter(VideoTranscript.video_id == video.id).first()
    transcript_ready = transcript_row and (
        not getattr(transcript_row, "status", None) or getattr(transcript_row, "status", "ready") == "ready"
    )
    if transcript_ready and transcript_row and transcript_row.transcript_text and transcript_row.transcript_text.strip():
        return transcript_row.transcript_text.strip(), "subtitle_text"

    tags = ", ".join([tag.strip() for tag in (video.tags or "").split(",") if tag.strip()])
    metadata_text = (
        f"Title: {video.title}. "
        f"Description: {video.description or 'No description provided.'}. "
        f"Category: {video.category or 'General'}. "
        f"Tags: {tags or 'none'}."
    )
    return metadata_text, "video_metadata"


def _summarize_mvp(source_text: str, max_sentences: int) -> str:
    normalized = " ".join(source_text.split())
    sentence_candidates = [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if s.strip()]
    chosen = sentence_candidates[:max_sentences]

    if not chosen:
        chosen = [_clip_text(normalized, 220)]

    summary = " ".join(chosen)
    return _clip_text(summary, SUMMARY_MAX_CHARS)


def _summary_input_hash(source_text: str, source_kind: str, max_sentences: int) -> str:
    material = f"{source_kind}|{max_sentences}|{source_text}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _tags_mvp(source_text: str, max_tags: int, allowed_tags: list[str]) -> list[str]:
    allowed = [_normalize_tag(t) for t in allowed_tags if _normalize_tag(t)]
    if not allowed:
        return []

    normalized_text = source_text.lower()
    scored: list[tuple[str, int]] = []
    for tag in allowed:
        parts = [p for p in tag.split("-") if len(p) >= 3]
        score = sum(1 for p in parts if p in normalized_text)
        scored.append((tag, score))

    ranked = sorted(scored, key=lambda x: (-x[1], x[0]))
    chosen = [tag for tag, score in ranked if score > 0][:max_tags]
    if chosen:
        return chosen
    if "general" in allowed:
        return ["general"]
    return allowed[:max_tags]


def _normalize_tag(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value[:32].strip("-")


def _ensure_tag_taxonomy_seed(db: Session) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seed_canonical = {_normalize_tag(key) for key in TAG_TAXONOMY_SEED.keys()}
    db.query(TagTaxonomy).filter(~TagTaxonomy.canonical_tag.in_(seed_canonical)).update(
        {TagTaxonomy.active: 0},
        synchronize_session=False,
    )

    # Build a deterministic alias->canonical mapping in memory first so we never
    # attempt duplicate alias inserts in a single transaction.
    planned_alias_owner: dict[str, str] = {}
    for canonical in TAG_TAXONOMY_SEED.keys():
        canonical_norm = _normalize_tag(canonical)
        if canonical_norm:
            planned_alias_owner[canonical_norm] = canonical_norm

    for canonical, meta in TAG_TAXONOMY_SEED.items():
        canonical_norm = _normalize_tag(canonical)
        if not canonical_norm:
            continue
        taxonomy_row = db.query(TagTaxonomy).filter(TagTaxonomy.canonical_tag == canonical_norm).first()
        if taxonomy_row:
            taxonomy_row.display_name = str(meta["display_name"])
            taxonomy_row.category = str(meta["category"])
            taxonomy_row.active = 1
        else:
            db.add(
                TagTaxonomy(
                    canonical_tag=canonical_norm,
                    display_name=str(meta["display_name"]),
                    category=str(meta["category"]),
                    active=1,
                    created_at=now,
                )
            )

        for alias in meta.get("aliases", []):
            alias_norm = _normalize_tag(str(alias))
            if not alias_norm:
                continue
            # Canonical tag name keeps ownership of same-name alias.
            if alias_norm in seed_canonical and alias_norm != canonical_norm:
                continue
            # First owner wins for ambiguous aliases in seed list.
            planned_alias_owner.setdefault(alias_norm, canonical_norm)

    existing_alias_rows = db.query(TagAlias).all()
    existing_alias_map = {row.alias: row for row in existing_alias_rows if row.alias}

    for alias_norm, canonical_norm in planned_alias_owner.items():
        existing = existing_alias_map.get(alias_norm)
        if existing:
            if existing.canonical_tag != canonical_norm:
                existing.canonical_tag = canonical_norm
            continue
        db.add(
            TagAlias(
                alias=alias_norm,
                canonical_tag=canonical_norm,
                created_at=now,
            )
        )

    for alias_norm, row in existing_alias_map.items():
        if alias_norm not in planned_alias_owner:
            db.delete(row)
    db.commit()


def _active_canonical_tags(db: Session) -> list[str]:
    rows = (
        db.query(TagTaxonomy.canonical_tag)
        .filter(TagTaxonomy.active == 1)
        .order_by(TagTaxonomy.canonical_tag.asc())
        .all()
    )
    return [row[0] for row in rows if row and row[0]]


def _canonicalize_tags(db: Session, tags: list[str], max_tags: int) -> list[str]:
    alias_rows = db.query(TagAlias).all()
    taxonomy_rows = db.query(TagTaxonomy).filter(TagTaxonomy.active == 1).all()
    active_set = {row.canonical_tag for row in taxonomy_rows}
    alias_to_canonical = {row.alias: row.canonical_tag for row in alias_rows if row.alias and row.canonical_tag}

    canonical_tags: list[str] = []
    for raw in tags:
        normalized = _normalize_tag(raw)
        if not normalized:
            continue
        canonical = alias_to_canonical.get(normalized, "")
        if not canonical and normalized in active_set:
            canonical = normalized
        if not canonical:
            continue
        if canonical not in canonical_tags:
            canonical_tags.append(canonical)
        if len(canonical_tags) >= max_tags:
            break
    return canonical_tags


def _infer_primary_category(db: Session, canonical_tags: list[str]) -> str | None:
    if not canonical_tags:
        return None
    rows = (
        db.query(TagTaxonomy.canonical_tag, TagTaxonomy.category)
        .filter(TagTaxonomy.active == 1)
        .all()
    )
    tag_to_category = {row[0]: row[1] for row in rows if row and row[0] and row[1]}
    counts: dict[str, int] = {}
    for tag in canonical_tags:
        category = tag_to_category.get(tag)
        if not category:
            continue
        counts[category] = counts.get(category, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _video_fallback_tags(video: Video) -> set[str]:
    return {_normalize_tag(tag) for tag in (video.tags or "").split(",") if _normalize_tag(tag)}


def _video_ai_tags_map(db: Session, video_ids: list[str]) -> dict[str, set[str]]:
    if not video_ids:
        return {}
    rows = db.query(VideoTag).filter(VideoTag.video_id.in_(video_ids)).all()
    result: dict[str, set[str]] = {}
    for row in rows:
        tag = _normalize_tag(row.tag or "")
        if not tag:
            continue
        result.setdefault(row.video_id, set()).add(tag)
    return result


def _recommendation_score_components(
    *,
    now: datetime,
    video: Video,
    tag_interest: dict[str, float],
    effective_tags: set[str],
    max_popularity: float,
    max_tag_overlap: float,
) -> tuple[float, float, float]:
    tag_overlap = sum(tag_interest.get(tag, 0.0) for tag in effective_tags)
    tag_overlap_norm = (tag_overlap / max_tag_overlap) if max_tag_overlap > 0 else 0.0

    age_seconds = max(1.0, (now - (video.created_at or now)).total_seconds())
    # Decays gradually over ~2 weeks.
    recency_score = math.exp(-age_seconds / (14 * 24 * 3600))

    popularity_raw = math.log1p(max(0, video.views) + 2 * max(0, video.likes))
    popularity_score = (popularity_raw / max_popularity) if max_popularity > 0 else 0.0
    return tag_overlap_norm, recency_score, popularity_score


def _tag_confidence_scores(
    db: Session,
    *,
    source_text: str,
    canonical_tags: list[str],
) -> dict[str, float]:
    if not canonical_tags:
        return {}
    # Confidence uses transcript evidence only. Title/description can be noisy
    # or in a different language and should not down-rank otherwise good tags.
    text = (source_text or "").lower()
    alias_rows = (
        db.query(TagAlias)
        .filter(TagAlias.canonical_tag.in_(canonical_tags))
        .all()
    )
    aliases_by_tag: dict[str, set[str]] = {tag: {tag} for tag in canonical_tags}
    for row in alias_rows:
        if row.canonical_tag in aliases_by_tag and row.alias:
            aliases_by_tag[row.canonical_tag].add(row.alias)

    scores: dict[str, float] = {}
    for tag in canonical_tags:
        score = 0.0
        parts = [p for p in tag.split("-") if len(p) >= 3]
        if parts:
            part_hits = sum(1 for p in parts if p in text)
            score += 0.4 * (part_hits / len(parts))
        alias_hits = sum(1 for alias in aliases_by_tag.get(tag, set()) if alias and alias in text)
        if alias_hits > 0:
            score += min(0.5, 0.2 + 0.1 * alias_hits)
        if tag in text:
            score += 0.2
        scores[tag] = min(1.0, score)
    return scores


def _serialize_summary_row(row: VideoSummary, *, cached: bool = False) -> dict:
    return {
        "video_id": row.video_id,
        "status": row.status,
        "summary": row.summary,
        "source_kind": row.source_kind,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "provider": row.provider,
        "error_message": row.error_message,
        "cached": cached,
        "retry_count": row.retry_count,
        "duration_ms": row.duration_ms,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _upsert_summary_job(
    db: Session,
    *,
    video_id: str,
    status: str,
    source_kind: str,
    max_sentences: int,
    input_hash: str,
    summary: str | None = None,
    provider: str | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
    bump_retry: bool = False,
) -> VideoSummary:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = db.query(VideoSummary).filter(VideoSummary.video_id == video_id).first()
    if row:
        row.status = status
        row.source_kind = source_kind
        row.max_sentences = max_sentences
        row.input_hash = input_hash
        row.summary = summary
        row.provider = provider
        row.error_message = error_message
        row.duration_ms = duration_ms
        row.generated_at = now if status == "ready" else row.generated_at
        row.updated_at = now
        if bump_retry:
            row.retry_count = (row.retry_count or 0) + 1
    else:
        row = VideoSummary(
            video_id=video_id,
            status=status,
            summary=summary,
            source_kind=source_kind,
            provider=provider,
            error_message=error_message,
            input_hash=input_hash,
            max_sentences=max_sentences,
            retry_count=1 if bump_retry else 0,
            duration_ms=duration_ms,
            generated_at=now if status == "ready" else None,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


async def _proxy_ai_health() -> dict | None:
    if not INTELLIGENCE_API_BASE_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{INTELLIGENCE_API_BASE_URL}/ai/health")
            response.raise_for_status()
            payload = response.json()
            payload["provider"] = "intelligence_service"
            return payload
    except Exception:
        logger.exception("Failed to fetch AI health from intelligence service")
        return None


async def _proxy_ai_summarize(payload: dict) -> dict | None:
    if not INTELLIGENCE_API_BASE_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{INTELLIGENCE_API_BASE_URL}/ai/summarize",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            result["provider"] = "intelligence_service"
            return result
    except Exception:
        logger.exception("Failed to proxy AI summarize to intelligence service")
        return None


def _proxy_ai_summarize_sync(payload: dict) -> dict | None:
    if not INTELLIGENCE_API_BASE_URL:
        return None

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(
                f"{INTELLIGENCE_API_BASE_URL}/ai/summarize",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            result["provider"] = "intelligence_service"
            return result
    except Exception:
        logger.exception("Failed to proxy AI summarize synchronously to intelligence service")
        return None


def _proxy_ai_tagging_sync(payload: dict) -> dict | None:
    if not INTELLIGENCE_API_BASE_URL:
        return None
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(
                f"{INTELLIGENCE_API_BASE_URL}/ai/tagging",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except Exception:
        logger.exception("Failed to proxy AI tagging synchronously to intelligence service")
        return None


def _replace_video_tags(db: Session, video_id: str, tags: list[str]) -> list[str]:
    db.query(VideoTag).filter(VideoTag.video_id == video_id).delete(synchronize_session=False)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    normalized: list[str] = []
    for tag in tags:
        t = re.sub(r"[^a-z0-9-]", "", tag.strip().lower())[:32]
        if not t or t in normalized:
            continue
        normalized.append(t)
        db.add(VideoTag(video_id=video_id, tag=t, created_at=now))
    db.commit()
    return normalized


def _run_summary_job(
    *,
    db_bind,
    video_id: str,
    source_text: str,
    source_kind: str,
    max_sentences: int,
    input_hash: str,
) -> None:
    session_factory = sessionmaker(bind=db_bind, autocommit=False, autoflush=False)
    db = session_factory()
    started = time.perf_counter()
    try:
        _upsert_summary_job(
            db,
            video_id=video_id,
            status="processing",
            source_kind=source_kind,
            max_sentences=max_sentences,
            input_hash=input_hash,
            summary=None,
            provider=None,
            error_message=None,
            duration_ms=None,
        )

        if source_kind == "video_metadata":
            deadline = time.time() + max(0, SUMMARY_WAIT_TRANSCRIPT_SECONDS)
            while time.time() < deadline:
                transcript_row = (
                    db.query(VideoTranscript)
                    .filter(VideoTranscript.video_id == video_id)
                    .first()
                )
                if not transcript_row:
                    break
                transcript_status = (transcript_row.status or "").strip().lower()
                if transcript_status == "ready" and (transcript_row.transcript_text or "").strip():
                    source_text = transcript_row.transcript_text.strip()
                    source_kind = "subtitle_text"
                    input_hash = _summary_input_hash(source_text, source_kind, max_sentences)
                    break
                if transcript_status == "failed":
                    break
                if transcript_status in {"queued", "processing", "pending", ""}:
                    time.sleep(max(0.1, SUMMARY_WAIT_TRANSCRIPT_POLL_SECONDS))
                    continue
                break

        proxied = _proxy_ai_summarize_sync(
            {
                "video_id": video_id,
                "source_text": source_text,
                "source_kind": source_kind,
                "max_sentences": max_sentences,
            }
        )
        if proxied and proxied.get("summary"):
            summary = _clip_text(str(proxied["summary"]), SUMMARY_MAX_CHARS)
            provider = str(proxied.get("provider") or "intelligence_service")
        else:
            summary = _summarize_mvp(source_text, max_sentences)
            provider = "dashboard_fallback"

        duration_ms = int((time.perf_counter() - started) * 1000)
        row = _upsert_summary_job(
            db,
            video_id=video_id,
            status="ready",
            source_kind=source_kind,
            max_sentences=max_sentences,
            input_hash=input_hash,
            summary=summary,
            provider=provider,
            error_message=None,
            duration_ms=duration_ms,
        )
        logger.info(
            "ai_summary_ready video_id=%s status=%s source_kind=%s provider=%s chars=%s duration_ms=%s retries=%s",
            row.video_id,
            row.status,
            row.source_kind,
            row.provider,
            len(row.summary or ""),
            row.duration_ms,
            row.retry_count,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        try:
            row = _upsert_summary_job(
                db,
                video_id=video_id,
                status="failed",
                source_kind=source_kind,
                max_sentences=max_sentences,
                input_hash=input_hash,
                summary=None,
                provider=None,
                error_message=str(exc)[:500],
                duration_ms=duration_ms,
            )
            logger.error(
                "ai_summary_failed video_id=%s status=%s source_kind=%s duration_ms=%s error=%s",
                row.video_id,
                row.status,
                row.source_kind,
                row.duration_ms,
                row.error_message,
            )
        except Exception:
            logger.exception("Failed to persist failed ai summary state video_id=%s", video_id)
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        _ensure_tag_taxonomy_seed(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard"}


@app.get("/ai/health")
async def ai_health():
    proxied = await _proxy_ai_health()
    if proxied:
        return proxied

    return {
        "status": "ok",
        "service": "ai-intelligence-mvp",
        "provider": "dashboard_fallback",
    }


@app.get("/ai/summarize/{video_id}")
def ai_summarize_status(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    row = db.query(VideoSummary).filter(VideoSummary.video_id == video_id).first()
    if not row:
        return {
            "video_id": video_id,
            "status": "pending",
            "summary": None,
            "source_kind": None,
            "generated_at": None,
            "provider": None,
            "error_message": None,
            "cached": False,
            "retry_count": 0,
            "duration_ms": None,
            "updated_at": None,
        }
    return _serialize_summary_row(row, cached=False)


@app.post("/ai/summarize")
async def ai_summarize(
    payload: SummarizeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    source_text, source_kind = _build_summary_source_text(
        db=db,
        video=video,
        subtitle_text=payload.subtitle_text,
    )
    input_hash = _summary_input_hash(source_text, source_kind, payload.max_sentences)
    row = db.query(VideoSummary).filter(VideoSummary.video_id == video.id).first()
    if row and row.input_hash == input_hash and not payload.force_refresh:
        if row.status == "ready":
            return _serialize_summary_row(row, cached=True)
        if row.status in {"queued", "processing"}:
            return _serialize_summary_row(row, cached=False)

    queued = _upsert_summary_job(
        db,
        video_id=video.id,
        status="queued",
        source_kind=source_kind,
        max_sentences=payload.max_sentences,
        input_hash=input_hash,
        summary=None,
        provider=None,
        error_message=None,
        duration_ms=None,
        bump_retry=payload.force_refresh,
    )
    background_tasks.add_task(
        _run_summary_job,
        db_bind=db.get_bind(),
        video_id=video.id,
        source_text=source_text,
        source_kind=source_kind,
        max_sentences=payload.max_sentences,
        input_hash=input_hash,
    )
    return _serialize_summary_row(queued, cached=False)


@app.post("/ai/summarize/{video_id}/retry")
async def ai_summarize_retry(
    video_id: str,
    background_tasks: BackgroundTasks,
    max_sentences: int = Query(3, ge=1, le=5),
    db: Session = Depends(get_db),
):
    payload = SummarizeRequest(
        video_id=video_id,
        subtitle_text=None,
        max_sentences=max_sentences,
        force_refresh=True,
    )
    return await ai_summarize(payload=payload, background_tasks=background_tasks, db=db)


@app.post("/ai/tagging")
def ai_tagging(payload: TaggingRequest, db: Session = Depends(get_db)):
    _ensure_tag_taxonomy_seed(db)
    allowed_tags = _active_canonical_tags(db)

    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript_row = db.query(VideoTranscript).filter(VideoTranscript.video_id == video.id).first()
    if not transcript_row or not (transcript_row.transcript_text or "").strip():
        raise HTTPException(status_code=409, detail="Transcript not ready for tagging")

    transcript_status = (transcript_row.status or "ready").strip().lower()
    if transcript_status != "ready":
        if transcript_status in {"queued", "processing", "pending"}:
            raise HTTPException(status_code=409, detail="Transcript not ready for tagging")
        raise HTTPException(status_code=409, detail="Transcript failed; cannot generate AI tags")

    source_text = transcript_row.transcript_text.strip()
    proxied = _proxy_ai_tagging_sync(
        {
            "video_id": video.id,
            "source_text": source_text,
            "title": video.title,
            "description": video.description,
            "source_category": video.category,
            "max_tags": payload.max_tags,
            "allowed_tags": allowed_tags,
        }
    )
    provider = "intelligence_service"
    raw_tags: list[str] = []
    if proxied and isinstance(proxied.get("tags"), list):
        raw_tags = [str(t) for t in proxied["tags"]]
        provider = str(proxied.get("provider") or "intelligence_service")
    if not raw_tags:
        raw_tags = _tags_mvp(source_text, payload.max_tags, allowed_tags)
        provider = "dashboard_fallback"

    canonical_tags = _canonicalize_tags(db, raw_tags, payload.max_tags)
    if not canonical_tags:
        canonical_tags = _canonicalize_tags(
            db,
            _tags_mvp(source_text, payload.max_tags * 2, allowed_tags),
            payload.max_tags,
        )
        provider = "dashboard_fallback"

    confidence_scores = _tag_confidence_scores(
        db,
        source_text=source_text,
        canonical_tags=canonical_tags[: payload.max_tags],
    )
    max_confidence = max(confidence_scores.values()) if confidence_scores else 0.0
    primary_category = _infer_primary_category(db, canonical_tags[: payload.max_tags])
    confidence_mode = "normal"
    tags_to_store = canonical_tags[: payload.max_tags]
    if provider != "openai" and max_confidence < TAG_LOW_CONFIDENCE_THRESHOLD:
        # Low-confidence case: keep at least one best-effort tag so UI/recommendation
        # still has a usable signal instead of returning an empty tag set.
        ranked_conf = sorted(
            confidence_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if ranked_conf:
            tags_to_store = [ranked_conf[0][0]]
            confidence_mode = "low_confidence_single_tag"
        else:
            tags_to_store = canonical_tags[:1]
            confidence_mode = "low_confidence_single_tag"

    stored_tags = _replace_video_tags(db, video.id, tags_to_store)
    return {
        "video_id": video.id,
        "tags": stored_tags,
        "primary_category": primary_category,
        "provider": provider,
        "confidence_mode": confidence_mode,
        "max_confidence": round(max_confidence, 3),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ai/tags/{video_id}")
def ai_tags(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    rows = (
        db.query(VideoTag)
        .filter(VideoTag.video_id == video_id)
        .order_by(VideoTag.created_at.desc(), VideoTag.tag.asc())
        .all()
    )
    return {
        "video_id": video_id,
        "tags": [row.tag for row in rows],
        "primary_category": _infer_primary_category(db, [row.tag for row in rows]) or _normalize_tag(video.category),
    }


@app.get("/ai/tag-taxonomy")
def ai_tag_taxonomy(db: Session = Depends(get_db)):
    _ensure_tag_taxonomy_seed(db)
    rows = (
        db.query(TagTaxonomy)
        .filter(TagTaxonomy.active == 1)
        .order_by(TagTaxonomy.category.asc(), TagTaxonomy.display_name.asc())
        .all()
    )
    return {
        "tags": [
            {
                "canonical_tag": row.canonical_tag,
                "display_name": row.display_name,
                "category": row.category,
            }
            for row in rows
        ]
    }


@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    user_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """Filter and rank videos by keyword match on title.
       Called when the user submits a search query.
       If user_id is provided, the query is recorded in search history.
       Returns full video objects for all matches.
    """
    logger.info("Search requested: %s", q)
    videos = db.query(Video).filter(Video.title.ilike(f"%{q}%")).all()

    if user_id:
        db.add(SearchHistory(user_id=user_id, query=q, searched_at=datetime.now(timezone.utc)))
        db.commit()

    return {"query": q, "results": [serialize_video(v) for v in videos]}


@app.get("/search/suggestions")
def search_suggestions(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Return up to 10 video title suggestions matching the query.
       Called when the user types in the search bar (expect to be called for every keystroke).       
       Returns a list of suggested video titles (not full video objects)
    """
    logger.info("Search suggestions requested: %s", q)
    rows = db.query(Video.title).filter(Video.title.ilike(f"%{q}%")).limit(10).all()
    return {"query": q, "suggestions": [row.title for row in rows]}


@app.get("/search/history")
def search_history(
    user_id: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return recent search queries for a user in reverse order."""
    logger.info("Search history requested for user %s", user_id)
    rows = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.searched_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "user_id": user_id,
        "history": [
            {"query": r.query, "searched_at": r.searched_at.isoformat()}
            for r in rows
        ],
    }


@app.get("/search/users")
def search_users(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Return active users whose name matches the query."""
    logger.info("User search requested: %s", q)
    users = (
        db.query(User)
        .filter(User.is_active == True, User.name.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    return {
        "query": q,
        "results": [{"id": u.id, "name": u.name, "role": u.role} for u in users],
    }


@app.get("/subscriptions/feed")
def subscriptions_feed(
    user_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return latest videos from channels the user subscribes to, in reverse chronological order."""
    logger.info("Subscriptions feed requested for user %s", user_id)
    subs = db.query(Subscription).filter(Subscription.subscriber_user_id == user_id).all()
    channel_ids = [s.channel_user_id for s in subs]
    if not channel_ids:
        return {"user_id": user_id, "videos": []}
    videos = (
        db.query(Video)
        .filter(Video.uploader_id.in_([int(c) for c in channel_ids]))
        .order_by(Video.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"user_id": user_id, "videos": [serialize_video(v) for v in videos]}


@app.get("/subscriptions/channel-subscribers")
def list_channel_subscribers(
    channel_user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """List subscriber user IDs for the given channel (users who subscribed to this channel)."""
    rows = (
        db.query(Subscription)
        .filter(Subscription.channel_user_id == channel_user_id)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    return {
        "channel_user_id": channel_user_id,
        "subscriber_user_ids": [row.subscriber_user_id for row in rows],
        "count": len(rows),
    }


@app.get("/subscriptions")
def list_subscriptions(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """List channel user IDs that the given user is subscribed to."""
    rows = (
        db.query(Subscription)
        .filter(Subscription.subscriber_user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    return {
        "user_id": user_id,
        "channel_user_ids": [row.channel_user_id for row in rows],
        "count": len(rows),
    }


@app.post("/subscriptions")
async def subscribe(
    subscriber_user_id: str = Query(..., min_length=1),
    channel_user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Create a subscription relationship (idempotent)."""
    if subscriber_user_id == channel_user_id:
        raise HTTPException(status_code=400, detail="You cannot subscribe to yourself")

    existing = (
        db.query(Subscription)
        .filter(Subscription.subscriber_user_id == subscriber_user_id)
        .filter(Subscription.channel_user_id == channel_user_id)
        .first()
    )
    if existing:
        return {
            "subscriber_user_id": subscriber_user_id,
            "channel_user_id": channel_user_id,
            "subscribed": True,
        }

    db.add(
        Subscription(
            subscriber_user_id=subscriber_user_id,
            channel_user_id=channel_user_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    await _send_subscription_notifications(subscriber_user_id, channel_user_id)

    return {
        "subscriber_user_id": subscriber_user_id,
        "channel_user_id": channel_user_id,
        "subscribed": True,
    }


@app.delete("/subscriptions")
def unsubscribe(
    subscriber_user_id: str = Query(..., min_length=1),
    channel_user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Delete an existing subscription relationship."""
    row = (
        db.query(Subscription)
        .filter(Subscription.subscriber_user_id == subscriber_user_id)
        .filter(Subscription.channel_user_id == channel_user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    db.delete(row)
    db.commit()

    return {
        "subscriber_user_id": subscriber_user_id,
        "channel_user_id": channel_user_id,
        "subscribed": False,
    }


@app.post("/user/history/watched")
def record_watch(
    user_id: str = Query(...),
    video_id: str = Query(...),
    position_seconds: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Record or update a watch event for a user.
       Upserts: if the user has watched this video before, updates last_watched_at and last_position_seconds.
    """
    logger.info("Recording watch for user %s, video %s", user_id, video_id)
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    row = db.query(WatchHistory).filter(
        WatchHistory.user_id == user_id,
        WatchHistory.video_id == video_id,
    ).first()

    if row:
        row.last_watched_at = datetime.now(timezone.utc)
        row.last_position_seconds = position_seconds
    else:
        db.add(WatchHistory(
            user_id=user_id,
            video_id=video_id,
            last_position_seconds=position_seconds,
            last_watched_at=datetime.now(timezone.utc),
        ))
    db.commit()
    return {"status": "recorded", "user_id": user_id, "video_id": video_id}


@app.get("/user/history/watched")
def watched_history(
    user_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return recently watched videos for a user in reverse chronological order."""
    logger.info("Watch history requested for user %s", user_id)
    rows = (
        db.query(WatchHistory)
        .filter(WatchHistory.user_id == user_id)
        .order_by(WatchHistory.last_watched_at.desc())
        .limit(limit)
        .all()
    )
    video_ids = [r.video_id for r in rows]
    videos_by_id = {
        v.id: v for v in db.query(Video).filter(Video.id.in_(video_ids)).all()
    }
    result = []
    for r in rows:
        if r.video_id in videos_by_id:
            video_data = serialize_video(videos_by_id[r.video_id])
            video_data["last_watched_at"] = r.last_watched_at.isoformat()
            video_data["last_position_seconds"] = r.last_position_seconds
            result.append(video_data)
    return {"user_id": user_id, "videos": result}


@app.get("/user/notifications")
def notifications(
    user_id: str = Query(...),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return recent notifications (read/unread) for a user in reverse chronological order."""
    logger.info("Notifications requested for user %s", user_id)
    query = db.query(Notification).filter(Notification.recipient_user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return {
        "user_id": user_id,
        "notifications": [
            {
                "notification_id": r.notification_id,
                "type": r.type,
                "title": r.title,
                "message": r.message,
                "actor_user_id": r.actor_user_id,
                "video_id": r.video_id,
                "is_read": r.is_read,
                "read_at": r.read_at.isoformat() if r.read_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@app.get("/dashboard/recommend")
def recommend(
    user_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return recommended videos.
    - No user_id: newest-first fallback.
    - With user_id and watch history: rank by tag overlap + recency + popularity.
    """
    logger.info("Recommend requested user_id=%s", user_id)
    base_query = db.query(Video)
    if user_id:
        try:
            base_query = base_query.filter(Video.uploader_id != int(user_id))
        except (ValueError, TypeError):
            pass
    videos = base_query.order_by(Video.created_at.desc()).all()
    if not videos:
        return {"videos": []}

    if not user_id:
        return {"videos": [serialize_video(v) for v in videos]}

    history_rows = (
        db.query(WatchHistory)
        .filter(WatchHistory.user_id == user_id)
        .order_by(WatchHistory.last_watched_at.desc())
        .limit(80)
        .all()
    )
    if not history_rows:
        return {"videos": [serialize_video(v) for v in videos]}

    watched_ids = {row.video_id for row in history_rows}
    video_ids = [v.id for v in videos]
    ai_tags_by_video = _video_ai_tags_map(db, video_ids)
    effective_tags_by_video: dict[str, set[str]] = {}
    for video in videos:
        ai_tags = ai_tags_by_video.get(video.id, set())
        fallback_tags = _video_fallback_tags(video)
        effective_tags_by_video[video.id] = ai_tags or fallback_tags

    tag_interest: dict[str, float] = {}
    history_count = len(history_rows)
    for idx, row in enumerate(history_rows):
        tags = effective_tags_by_video.get(row.video_id, set())
        if not tags:
            continue
        recency_weight = max(1.0, float(history_count - idx))
        completion_bonus = min(1.0, max(0.0, float(row.last_position_seconds or 0)) / 180.0)
        weight = 1.0 + (0.12 * recency_weight) + (0.25 * completion_bonus)
        for tag in tags:
            tag_interest[tag] = tag_interest.get(tag, 0.0) + weight

    if not tag_interest:
        return {"videos": [serialize_video(v) for v in videos]}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    overlap_candidates = [
        sum(tag_interest.get(tag, 0.0) for tag in effective_tags_by_video.get(video.id, set()))
        for video in videos
    ]
    max_tag_overlap = max(overlap_candidates) if overlap_candidates else 0.0
    max_popularity = max(
        (math.log1p(max(0, v.views) + 2 * max(0, v.likes)) for v in videos),
        default=0.0,
    )

    scored: list[tuple[float, datetime, Video]] = []
    for video in videos:
        overlap_score, recency_score, popularity_score = _recommendation_score_components(
            now=now,
            video=video,
            tag_interest=tag_interest,
            effective_tags=effective_tags_by_video.get(video.id, set()),
            max_popularity=max_popularity,
            max_tag_overlap=max_tag_overlap,
        )
        score = 0.65 * overlap_score + 0.20 * recency_score + 0.15 * popularity_score
        scored.append((score, video.created_at or datetime.min, video))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    unseen = [video for _, _, video in scored if video.id not in watched_ids]
    ranked = unseen if unseen else [video for _, _, video in scored]
    return {"videos": [serialize_video(v) for v in ranked]}
