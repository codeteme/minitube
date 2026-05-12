from src.video_crud_service.models import Video, VideoTranscript
from .conftest import create_test_video


def test_get_all_videos_empty(client):
    """Test getting videos when none exist."""
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_videos_with_data(client, test_db):
    """Test getting all videos."""
    video1 = create_test_video(test_db, title="Video 1", uploader_id=1)
    video2 = create_test_video(test_db, title="Video 2", uploader_id=2)
    
    response = client.get("/videos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == video1.id
    assert data[1]["id"] == video2.id


def test_get_video_by_id(client, test_db):
    """Test retrieving a single video by ID."""
    video = create_test_video(test_db, title="My Video")
    
    response = client.get(f"/videos/{video.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video.id
    assert data["title"] == "My Video"
    assert data["uploader_id"] == 1
    assert data["description"] == "Test description"
    assert data["views"] == 0
    assert data["likes"] == 0


def test_get_video_not_found(client):
    """Test retrieving a non-existent video."""
    response = client.get("/videos/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_serialized_video_structure(client, test_db):
    """Test that serialized video has all required fields."""
    video = create_test_video(test_db, title="Structure Test")
    
    response = client.get(f"/videos/{video.id}")
    data = response.json()
    
    required_fields = {
        "id", "title", "description", "category", "tags",
        "thumbnail_url", "uploader_id", "original_filename",
        "saved_filename", "content_type", "size", "path",
        "views", "likes", "duration_seconds", "playback_url",
        "created_at"
    }
    assert required_fields.issubset(data.keys())
    assert data["playback_url"] == f"/videos/{video.id}/play"
    assert data["thumbnail_url"] == f"/videos/{video.id}/thumbnail"


def test_get_video_transcript_pending_when_not_ready(client, test_db):
    video = create_test_video(test_db, title="Transcript pending")
    response = client.get(f"/videos/{video.id}/transcript")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == video.id
    assert data["status"] == "pending"
    assert data["transcript_text"] == ""


def test_get_video_transcript_ready(client, test_db):
    video = create_test_video(test_db, title="Transcript ready")
    row = VideoTranscript(
        video_id=video.id,
        transcript_text="Hello from ASR.",
        source="faster_whisper",
        status="ready",
        error_message=None,
        language="en",
    )
    test_db.add(row)
    test_db.commit()

    response = client.get(f"/videos/{video.id}/transcript")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == video.id
    assert data["status"] == "ready"
    assert data["transcript_text"] == "Hello from ASR."
    assert data["source"] == "faster_whisper"
