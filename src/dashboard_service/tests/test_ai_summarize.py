import time

from .conftest import create_test_video, create_test_transcript


def _wait_ready_status(client, video_id: str, timeout_seconds: float = 2.0) -> dict:
    deadline = time.time() + timeout_seconds
    latest = {}
    while time.time() < deadline:
        response = client.get(f"/ai/summarize/{video_id}")
        assert response.status_code == 200
        latest = response.json()
        if latest.get("status") in {"ready", "failed"}:
            return latest
        time.sleep(0.05)
    return latest


def test_ai_health(client):
    response = client.get("/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-intelligence-mvp"


def test_ai_summarize_video_not_found(client):
    response = client.post("/ai/summarize", json={"video_id": "missing"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_ai_summarize_status_video_not_found(client):
    response = client.get("/ai/summarize/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_ai_summarize_from_video_metadata(client, test_db):
    video = create_test_video(
        test_db,
        title="Intro to Distributed Systems",
        uploader_id=7,
    )

    kickoff = client.post(
        "/ai/summarize",
        json={"video_id": video.id, "max_sentences": 2},
    )
    assert kickoff.status_code == 200
    assert kickoff.json()["status"] in {"queued", "processing", "ready"}

    data = _wait_ready_status(client, video.id)
    assert data["video_id"] == video.id
    assert data["status"] == "ready"
    assert data["source_kind"] == "video_metadata"
    assert isinstance(data["summary"], str)
    assert len(data["summary"]) > 0
    assert "Intro to Distributed Systems" in data["summary"]


def test_ai_summarize_uses_subtitle_text_when_provided(client, test_db):
    video = create_test_video(test_db, title="Any title", uploader_id=8)
    subtitle_text = (
        "This lesson explains rate limiting in API gateways. "
        "Then it compares token bucket and leaky bucket with examples."
    )

    kickoff = client.post(
        "/ai/summarize",
        json={
            "video_id": video.id,
            "subtitle_text": subtitle_text,
            "max_sentences": 1,
        },
    )
    assert kickoff.status_code == 200

    data = _wait_ready_status(client, video.id)
    assert data["status"] == "ready"
    assert data["source_kind"] == "subtitle_text"
    assert "rate limiting in API gateways" in (data["summary"] or "")


def test_ai_summarize_uses_stored_transcript_when_available(client, test_db):
    video = create_test_video(test_db, title="Cloud databases", uploader_id=9)
    create_test_transcript(
        test_db,
        video_id=video.id,
        transcript_text=(
            "Today we explain replication lag in distributed databases. "
            "Then we compare eventual consistency and strong consistency."
        ),
    )

    kickoff = client.post(
        "/ai/summarize",
        json={
            "video_id": video.id,
            "max_sentences": 1,
        },
    )
    assert kickoff.status_code == 200

    data = _wait_ready_status(client, video.id)
    assert data["status"] == "ready"
    assert data["source_kind"] == "subtitle_text"
    assert "replication lag in distributed databases" in (data["summary"] or "")


def test_ai_summarize_cached_result_is_reused(client, test_db):
    video = create_test_video(test_db, title="Caching test", uploader_id=10)
    client.post("/ai/summarize", json={"video_id": video.id, "max_sentences": 2})
    ready = _wait_ready_status(client, video.id)
    assert ready["status"] == "ready"

    second = client.post("/ai/summarize", json={"video_id": video.id, "max_sentences": 2})
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "ready"
    assert payload["cached"] is True
    assert payload["summary"] == ready["summary"]


def test_ai_summarize_retry_bumps_retry_count(client, test_db):
    video = create_test_video(test_db, title="Retry test", uploader_id=11)
    client.post("/ai/summarize", json={"video_id": video.id})
    first_ready = _wait_ready_status(client, video.id)
    assert first_ready["status"] == "ready"
    first_retries = first_ready["retry_count"]

    retry_resp = client.post(f"/ai/summarize/{video.id}/retry?max_sentences=3")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] in {"queued", "processing", "ready"}

    second_ready = _wait_ready_status(client, video.id)
    assert second_ready["status"] == "ready"
    assert second_ready["retry_count"] >= first_retries + 1
