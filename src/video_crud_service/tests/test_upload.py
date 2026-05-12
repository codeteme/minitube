from pathlib import Path
from unittest.mock import AsyncMock, patch
from src.video_crud_service.models import Video


def test_upload_video_success(client, test_db, sample_video_file, tmp_path):
    """Test successful video upload."""
    # Mock the upload directory and thumbnail generation
    with patch("src.video_crud_service.videos.UPLOAD_DIR", tmp_path):
        with patch("src.video_crud_service.videos._generate_thumbnail", return_value=False):
            with patch("src.video_crud_service.videos._notify_subscribers_new_video", new_callable=AsyncMock) as mock_notify:
                response = client.post(
                    "/videos/upload",
                    data={
                        "title": "My Test Video",
                        "description": "A great video",
                        "category": "Technology",
                        "tags": "technology, education",
                        "uploader_id": 1,
                        "views": 5,
                        "likes": 2,
                        "duration_seconds": 120,
                    },
                    files={"file": ("test.mp4", sample_video_file, "video/mp4")},
                )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "My Test Video"
    assert data["description"] == "A great video"
    assert data["category"] == "Technology"
    assert data["uploader_id"] == 1
    assert data["views"] == 5
    assert data["likes"] == 2
    assert data["duration_seconds"] == 120
    assert "id" in data
    assert len(data["id"]) > 0
    
    # Verify in database
    videos = test_db.query(Video).all()
    assert len(videos) == 1
    assert videos[0].title == "My Test Video"
    assert videos[0].tags == "technology,education"
    mock_notify.assert_awaited_once()


def test_upload_rejects_non_canonical_tag(client, sample_video_file, tmp_path):
    with patch("src.video_crud_service.videos.UPLOAD_DIR", tmp_path):
        with patch("src.video_crud_service.videos._generate_thumbnail", return_value=False):
            response = client.post(
                "/videos/upload",
                data={
                    "title": "Bad tags",
                    "uploader_id": 1,
                    "tags": "my-custom-tag",
                },
                files={"file": ("test.mp4", sample_video_file, "video/mp4")},
            )

    assert response.status_code == 400
    assert "canonical options only" in response.json()["detail"]


def test_upload_invalid_file_type(client):
    """Test upload with unsupported file type."""
    response = client.post(
        "/videos/upload",
        data={
            "title": "Bad Video",
            "uploader_id": 1,
        },
        files={"file": ("test.txt", b"not a video", "text/plain")},
    )
    
    assert response.status_code == 400
    assert "Unsupported video type" in response.json()["detail"]


def test_upload_missing_required_field(client):
    """Test upload without required title field."""
    response = client.post(
        "/videos/upload",
        data={"uploader_id": 1},
        files={"file": ("test.mp4", b"fake", "video/mp4")},
    )
    
    assert response.status_code == 422  # Validation error


def test_upload_negative_views_converted_to_zero(client, test_db, sample_video_file, tmp_path):
    """Test that negative views/likes are converted to 0."""
    with patch("src.video_crud_service.videos.UPLOAD_DIR", tmp_path):
        with patch("src.video_crud_service.videos._generate_thumbnail", return_value=False):
            response = client.post(
                "/videos/upload",
                data={
                    "title": "Test",
                    "uploader_id": 1,
                    "views": -5,
                    "likes": -10,
                },
                files={"file": ("test.mp4", sample_video_file, "video/mp4")},
            )
    
    assert response.status_code == 200
    data = response.json()
    assert data["views"] == 0
    assert data["likes"] == 0


def test_upload_octet_stream_with_video_extension(client, sample_video_file, tmp_path):
    """Test upload with application/octet-stream mime type but video extension."""
    with patch("src.video_crud_service.videos.UPLOAD_DIR", tmp_path):
        with patch("src.video_crud_service.videos._generate_thumbnail", return_value=False):
            response = client.post(
                "/videos/upload",
                data={"title": "Test", "uploader_id": 1},
                files={"file": ("test.mp4", sample_video_file, "application/octet-stream")},
            )
    
    assert response.status_code == 200


def test_upload_notification_failure_does_not_fail_upload(client, sample_video_file, tmp_path):
    with patch("src.video_crud_service.videos.UPLOAD_DIR", tmp_path):
        with patch("src.video_crud_service.videos._generate_thumbnail", return_value=False):
            with patch(
                "src.video_crud_service.videos._notify_subscribers_new_video",
                new_callable=AsyncMock,
                side_effect=RuntimeError("notification failed"),
            ):
                response = client.post(
                    "/videos/upload",
                    data={"title": "Notification Resilience", "uploader_id": 1},
                    files={"file": ("test.mp4", sample_video_file, "video/mp4")},
                )

    assert response.status_code == 200
