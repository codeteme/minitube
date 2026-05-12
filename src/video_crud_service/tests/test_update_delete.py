from src.video_crud_service.main import app
from src.video_crud_service.models import Video, VideoSummary, VideoTag, VideoTranscript
from src.video_crud_service.videos import get_current_user_id
from .conftest import create_test_video


def test_update_video_title(client, test_db):
    """Test updating video title."""
    video = create_test_video(test_db, title="Original Title", uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"title": "Updated Title"})

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_video_multiple_fields(client, test_db):
    """Test updating multiple fields."""
    video = create_test_video(test_db)

    response = client.patch(
        f"/videos/{video.id}",
        data={
            "title": "New Title",
            "description": "New description",
            "category": "Gaming",
            "tags": "new, tags",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["description"] == "New description"
    assert data["category"] == "Gaming"


def test_update_video_unauthorized(client, test_db):
    """Test that non-owner cannot update video."""
    video = create_test_video(test_db, uploader_id=1)
    app.dependency_overrides[get_current_user_id] = lambda: 999

    try:
        response = client.patch(f"/videos/{video.id}", data={"title": "Hacked!"})
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: 1

    assert response.status_code == 403
    assert "do not own" in response.json()["detail"]


def test_update_nonexistent_video(client):
    """Test updating non-existent video."""
    response = client.patch("/videos/nonexistent", data={"title": "New"})

    assert response.status_code == 404


def test_update_empty_title_leaves_title_unchanged(client, test_db):
    """FastAPI treats an empty form string as None (not provided), so the
    title must remain unchanged rather than being overwritten with blank."""
    video = create_test_video(test_db, title="Original", uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"title": ""})

    assert response.status_code == 200
    assert response.json()["title"] == "Original"


def test_update_whitespace_only_title_rejected(client, test_db):
    """Whitespace-only title must be rejected with 422."""
    video = create_test_video(test_db, title="Original", uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"title": "   "})

    assert response.status_code == 422


def test_update_title_is_stripped(client, test_db):
    """Title with surrounding whitespace is saved trimmed."""
    video = create_test_video(test_db, title="Original", uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"title": "  New Title  "})

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


def test_update_invalid_category_rejected(client, test_db):
    """An unrecognised category must be rejected with 422."""
    video = create_test_video(test_db, uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"category": "InvalidCategory"})

    assert response.status_code == 422
    assert "Invalid category" in response.json()["detail"]


def test_update_valid_category_accepted(client, test_db):
    """A valid category is accepted."""
    video = create_test_video(test_db, uploader_id=1)

    response = client.patch(f"/videos/{video.id}", data={"category": "Music"})

    assert response.status_code == 200
    assert response.json()["category"] == "Music"


def test_delete_video(client, test_db):
    """Test deleting a video removes the video row."""
    video = create_test_video(test_db, uploader_id=1)
    video_id = video.id

    response = client.delete(f"/videos/{video_id}")

    assert response.status_code == 200
    assert response.json()["id"] == video_id

    deleted = test_db.query(Video).filter(Video.id == video_id).first()
    assert deleted is None


def test_delete_video_removes_transcript(client, test_db):
    """Deleting a video must also remove its VideoTranscript row."""
    video = create_test_video(test_db, uploader_id=1)
    video_id = video.id
    test_db.add(VideoTranscript(video_id=video_id, transcript_text="hello", status="ready"))
    test_db.commit()

    client.delete(f"/videos/{video_id}")

    test_db.expire_all()
    orphan = test_db.query(VideoTranscript).filter(VideoTranscript.video_id == video_id).first()
    assert orphan is None


def test_delete_video_removes_summary(client, test_db):
    """Deleting a video must also remove its VideoSummary row."""
    video = create_test_video(test_db, uploader_id=1)
    video_id = video.id
    test_db.add(VideoSummary(video_id=video_id, status="ready", summary="short summary"))
    test_db.commit()

    client.delete(f"/videos/{video_id}")

    test_db.expire_all()
    orphan = test_db.query(VideoSummary).filter(VideoSummary.video_id == video_id).first()
    assert orphan is None


def test_delete_video_removes_tags(client, test_db):
    """Deleting a video must also remove its VideoTag rows."""
    video = create_test_video(test_db, uploader_id=1)
    video_id = video.id
    test_db.add(VideoTag(video_id=video_id, tag="python"))
    test_db.add(VideoTag(video_id=video_id, tag="tutorial"))
    test_db.commit()

    client.delete(f"/videos/{video_id}")

    test_db.expire_all()
    orphans = test_db.query(VideoTag).filter(VideoTag.video_id == video_id).all()
    assert orphans == []


def test_delete_video_unauthorized(client, test_db):
    """Test that non-owner cannot delete video."""
    video = create_test_video(test_db, uploader_id=1)
    app.dependency_overrides[get_current_user_id] = lambda: 999

    try:
        response = client.delete(f"/videos/{video.id}")
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: 1

    assert response.status_code == 403
    assert "do not own" in response.json()["detail"]


def test_delete_nonexistent_video(client):
    """Test deleting non-existent video."""
    response = client.delete("/videos/nonexistent")

    assert response.status_code == 404
