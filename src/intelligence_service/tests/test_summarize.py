from fastapi.testclient import TestClient

from src.intelligence_service.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "intelligence"


def test_ai_summarize():
    response = client.post(
        "/ai/summarize",
        json={
            "video_id": "v-123",
            "source_text": "Sentence one. Sentence two. Sentence three.",
            "source_kind": "subtitle_text",
            "max_sentences": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "v-123"
    assert data["source_kind"] == "subtitle_text"
    assert "Sentence one." in data["summary"]


def test_ai_tagging():
    response = client.post(
        "/ai/tagging",
        json={
            "video_id": "v-123",
            "source_text": "This tutorial explains vector databases, embeddings, and semantic search retrieval.",
            "max_tags": 4,
            "allowed_tags": ["technology", "education", "ai-tools", "gaming", "music"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "v-123"
    assert isinstance(data["tags"], list)
    assert len(data["tags"]) > 0
