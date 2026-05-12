import re
import os
import logging
import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Intelligence Service")
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
OPENAI_SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
OPENAI_TAG_MODEL = os.getenv("OPENAI_TAG_MODEL", OPENAI_SUMMARY_MODEL).strip() or OPENAI_SUMMARY_MODEL
OPENAI_SUMMARY_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_SUMMARY_MAX_OUTPUT_TOKENS", "220"))
OPENAI_SUMMARY_MAX_CHARS = int(os.getenv("OPENAI_SUMMARY_MAX_CHARS", "2000"))
OPENAI_SUMMARY_ENABLED = os.getenv("OPENAI_SUMMARY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://vcm-52527.vm.duke.edu:5173", "http://vcm-52418.vm.duke.edu:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SummarizeRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    source_text: str = Field(..., min_length=1, max_length=20000)
    source_kind: str = Field(default="video_metadata", min_length=1, max_length=64)
    max_sentences: int = Field(default=3, ge=1, le=5)


class TaggingRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    source_text: str = Field(..., min_length=1, max_length=20000)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    source_category: str | None = Field(default=None, max_length=100)
    max_tags: int = Field(default=5, ge=1, le=10)
    allowed_tags: list[str] = Field(default_factory=list, max_length=200)


def _clip_text(value: str, max_length: int) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 3].rstrip()}..."


def _summarize_mvp(source_text: str, max_sentences: int) -> str:
    normalized = " ".join(source_text.split())
    sentence_candidates = [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if s.strip()]
    chosen = sentence_candidates[:max_sentences]
    if not chosen:
        chosen = [_clip_text(normalized, 220)]
    return _clip_text(" ".join(chosen), OPENAI_SUMMARY_MAX_CHARS)


def _normalize_tag(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    value = re.sub(r"\s+", "-", value)
    return value[:32].strip("-")


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


def _openai_summarize(source_text: str, max_sentences: int, source_kind: str) -> str | None:
    if not OPENAI_SUMMARY_ENABLED or not OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        logger.warning("OpenAI SDK unavailable, using rules fallback: %s", exc)
        return None

    source_note = (
        "Source is transcript text with spoken content."
        if source_kind == "subtitle_text"
        else "Source is metadata only (title/description/tags). Be conservative and avoid overclaiming specifics."
    )
    system_prompt = (
        "You summarize one video for end users.\n"
        "Rules:\n"
        "1) Be faithful to source; do not invent details.\n"
        "2) Plain English only, no markdown, no bullet points.\n"
        f"3) Output at most {max_sentences} sentence(s).\n"
        "4) Keep the most informative points first.\n"
        "5) If source is weak, state uncertainty briefly instead of hallucinating."
    )
    user_prompt = f"Source kind: {source_kind}\n{source_note}\n\nSource text:\n{source_text}"

    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
        response = client.responses.create(
            model=OPENAI_SUMMARY_MODEL,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            max_output_tokens=OPENAI_SUMMARY_MAX_OUTPUT_TOKENS,
        )
        output_text = getattr(response, "output_text", None)
        if not output_text or not str(output_text).strip():
            return None
        return _clip_text(str(output_text), OPENAI_SUMMARY_MAX_CHARS)
    except Exception:
        logger.exception("OpenAI summarize request failed, using rules fallback")
        return None


def _openai_tagging(
    source_text: str,
    max_tags: int,
    allowed_tags: list[str],
    *,
    title: str | None = None,
    description: str | None = None,
    source_category: str | None = None,
) -> list[str] | None:
    if not OPENAI_SUMMARY_ENABLED or not OPENAI_API_KEY:
        return None
    normalized_allowed = [_normalize_tag(t) for t in allowed_tags if _normalize_tag(t)]
    if not normalized_allowed:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        logger.warning("OpenAI SDK unavailable for tagging, using rules fallback: %s", exc)
        return None

    system_prompt = (
        "Select topic tags for a video using transcript + metadata.\n"
        "You must ONLY choose tags from the provided allowed tag list.\n"
        f"Return a JSON array with at most {max_tags} tags.\n"
        "Rules: no extra text, no markdown, no tags outside the allowed list, no duplicates.\n"
        "Pick specific high-confidence tags first; avoid overly generic tags unless evidence is weak."
    )
    user_prompt = (
        f"Title: {title or ''}\n"
        f"Description: {description or ''}\n"
        f"Uploader category hint: {source_category or ''}\n\n"
        f"Allowed tags: {', '.join(normalized_allowed)}\n\n"
        f"Transcript:\n{source_text}"
    )
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
        response = client.responses.create(
            model=OPENAI_TAG_MODEL,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            max_output_tokens=120,
        )
        output_text = getattr(response, "output_text", None)
        if not output_text:
            return None
        parsed = json.loads(str(output_text))
        if not isinstance(parsed, list):
            return None
        allowed_set = set(normalized_allowed)
        cleaned: list[str] = []
        for raw in parsed:
            if not isinstance(raw, str):
                continue
            tag = _normalize_tag(raw)
            if tag in allowed_set and tag not in cleaned:
                cleaned.append(tag)
            if len(cleaned) >= max_tags:
                break
        return cleaned or None
    except Exception:
        logger.exception("OpenAI tagging request failed, using rules fallback")
        return None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "intelligence"}


@app.get("/ai/health")
def ai_health() -> dict:
    provider = "openai" if OPENAI_SUMMARY_ENABLED and OPENAI_API_KEY else "rules-based-mvp"
    return {
        "status": "ok",
        "service": "ai-intelligence",
        "provider": provider,
        "model": OPENAI_SUMMARY_MODEL if provider == "openai" else None,
        "base_url": OPENAI_BASE_URL if provider == "openai" else None,
        "openai_configured": provider == "openai",
    }


@app.post("/ai/summarize")
def ai_summarize(payload: SummarizeRequest) -> dict:
    summary = _openai_summarize(payload.source_text, payload.max_sentences, payload.source_kind)
    provider = "openai" if summary else "rules-based-mvp"
    if not summary:
        summary = _summarize_mvp(payload.source_text, payload.max_sentences)

    return {
        "video_id": payload.video_id,
        "summary": summary,
        "source_kind": payload.source_kind,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": OPENAI_SUMMARY_MODEL if provider == "openai" else None,
    }


@app.post("/ai/tagging")
def ai_tagging(payload: TaggingRequest) -> dict:
    tags = _openai_tagging(
        payload.source_text,
        payload.max_tags,
        payload.allowed_tags,
        title=payload.title,
        description=payload.description,
        source_category=payload.source_category,
    )
    provider = "openai" if tags else "rules-based-mvp"
    if not tags:
        tags = _tags_mvp(payload.source_text, payload.max_tags, payload.allowed_tags)
    return {
        "video_id": payload.video_id,
        "tags": tags[:payload.max_tags],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": OPENAI_TAG_MODEL if provider == "openai" else None,
    }
