from pathlib import Path

from src.video_crud_service.models import Video
from .conftest import create_test_video


# --- GET /play: serves the file, never touches view count ---

def test_play_video_serves_file(client, test_db, tmp_path):
    """GET /play returns the video file and does not change the view count."""
    file_path = tmp_path / "playable.mp4"
    file_path.write_bytes(b"video-data")

    video = create_test_video(test_db, path=str(file_path), views=2)

    response = client.get(f"/videos/{video.id}/play")
    assert response.status_code == 200

    test_db.expire_all()
    unchanged = test_db.query(Video).filter(Video.id == video.id).first()
    assert unchanged.views == 2


def test_play_video_not_found(client, test_db):
    """GET /play on a missing video returns 404."""
    response = client.get("/videos/does-not-exist/play")
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_play_video_missing_file(client, test_db, tmp_path):
    """GET /play when the file is gone returns 404 and leaves views unchanged."""
    missing_path = tmp_path / "missing.mp4"
    video = create_test_video(test_db, path=str(missing_path), views=4)

    response = client.get(f"/videos/{video.id}/play")
    assert response.status_code == 404
    assert response.json()["detail"] == "Stored file not found"

    test_db.expire_all()
    unchanged = test_db.query(Video).filter(Video.id == video.id).first()
    assert unchanged.views == 4


# --- POST /view: increments view count exactly once per explicit client call ---

def test_record_view_increments_count(client, test_db, tmp_path):
    """POST /view increments view count by exactly one."""
    file_path = tmp_path / "v.mp4"
    file_path.write_bytes(b"video-data")
    video = create_test_video(test_db, path=str(file_path), views=2)

    response = client.post(f"/videos/{video.id}/view")
    assert response.status_code == 204

    test_db.expire_all()
    updated = test_db.query(Video).filter(Video.id == video.id).first()
    assert updated.views == 3


def test_record_view_called_twice_counts_twice(client, test_db, tmp_path):
    """Two POST /view calls produce two increments — the client guards against duplicates."""
    file_path = tmp_path / "v2.mp4"
    file_path.write_bytes(b"video-data")
    video = create_test_video(test_db, path=str(file_path), views=0)

    client.post(f"/videos/{video.id}/view")
    client.post(f"/videos/{video.id}/view")

    test_db.expire_all()
    updated = test_db.query(Video).filter(Video.id == video.id).first()
    assert updated.views == 2


def test_record_view_not_found(client, test_db):
    """POST /view on a missing video returns 404."""
    response = client.post("/videos/does-not-exist/view")
    assert response.status_code == 404
