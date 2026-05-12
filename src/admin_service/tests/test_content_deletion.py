import tempfile
from pathlib import Path

from src.admin_service.tests.conftest import seed_video, seed_user


def test_delete_content_removes_video_from_db(client, db):
    """Test DELETE /admin/content/{video_id} removes video from database."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp_path = tmp.name

    try:
        user = seed_user(db, name="Ian", email="ian@test.com", role="user", is_active=True)
        video = seed_video(
            db,
            id="vid-001",
            title="Test Video",
            uploader_id=user.id,
            path=tmp_path,
        )

        resp = client.delete(f"/admin/content/{video.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["video_id"] == video.id
        assert body["deleted"] is True

    finally:
        # Clean up temp file if it still exists
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_delete_nonexistent_video_returns_404(client, db):
    """Test DELETE /admin/content/{video_id} returns 404 for non-existent video."""
    resp = client.delete("/admin/content/nonexistent-id")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "Video not found"


def test_delete_content_with_missing_file(client, db):
    """Test DELETE /admin/content/{video_id} handles missing file gracefully."""
    user = seed_user(db, name="Jack", email="jack@test.com", role="user", is_active=True)
    # Point to a file that doesn't exist
    video = seed_video(
        db,
        id="vid-002",
        title="Video with Missing File",
        uploader_id=user.id,
        path="/nonexistent/path/to/video.mp4",
    )

    resp = client.delete(f"/admin/content/{video.id}")
    # Should still succeed (file doesn't exist, but video is removed from DB)
    assert resp.status_code == 200
    body = resp.json()
    assert body["video_id"] == video.id
    assert body["deleted"] is True


def test_delete_video_with_actual_file(client, db):
    """Test DELETE /admin/content/{video_id} removes both DB record and file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp_path = tmp.name
        tmp.write(b"fake video data")

    try:
        assert Path(tmp_path).exists()

        user = seed_user(db, name="Kate", email="kate@test.com", role="user", is_active=True)
        video = seed_video(
            db,
            id="vid-003",
            title="Video with Real File",
            uploader_id=user.id,
            path=tmp_path,
        )

        resp = client.delete(f"/admin/content/{video.id}")
        assert resp.status_code == 200

        # Verify file is deleted
        assert not Path(tmp_path).exists()

    finally:
        # Extra cleanup just in case
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_delete_multiple_videos_independently(client, db):
    """Test deleting multiple videos doesn't affect each other."""
    user = seed_user(db, name="Leo", email="leo@test.com", role="user", is_active=True)

    video1 = seed_video(
        db,
        id="vid-del-1",
        title="Video 1",
        uploader_id=user.id,
        path="/tmp/vid1.mp4",
    )
    video2 = seed_video(
        db,
        id="vid-del-2",
        title="Video 2",
        uploader_id=user.id,
        path="/tmp/vid2.mp4",
    )

    # Delete first video
    resp1 = client.delete(f"/admin/content/{video1.id}")
    assert resp1.status_code == 200

    # Second video should still not exist in DB (never seeded a real file)
    # but deletion should succeed
    resp2 = client.delete(f"/admin/content/{video2.id}")
    assert resp2.status_code == 200

    # Trying to delete again should fail
    resp3 = client.delete(f"/admin/content/{video1.id}")
    assert resp3.status_code == 404
