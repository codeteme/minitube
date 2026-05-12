from .conftest import create_test_video, create_test_watch_history


def test_record_watch_new_entry(client, test_db):
    """Test recording a watch event for a video not previously watched."""
    video = create_test_video(test_db, title="Test Video")
    user_id = "user1"
    
    response = client.post(
        f"/user/history/watched?user_id={user_id}&video_id={video.id}&position_seconds=30"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["user_id"] == user_id
    assert data["video_id"] == video.id


def test_record_watch_update_existing(client, test_db):
    """Test recording a watch event updates existing watch history."""
    video = create_test_video(test_db, title="Test Video")
    user_id = "user1"
    
    # First watch
    response = client.post(
        f"/user/history/watched?user_id={user_id}&video_id={video.id}&position_seconds=30"
    )
    assert response.status_code == 200
    
    # Second watch (update)
    response = client.post(
        f"/user/history/watched?user_id={user_id}&video_id={video.id}&position_seconds=60"
    )
    assert response.status_code == 200
    
    # Verify only one entry exists and position is updated
    response = client.get(f"/user/history/watched?user_id={user_id}")
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["last_position_seconds"] == 60


def test_record_watch_nonexistent_video(client):
    """Test recording a watch for a non-existent video returns 404."""
    response = client.post(
        "/user/history/watched?user_id=user1&video_id=nonexistent&position_seconds=0"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_record_watch_default_position(client, test_db):
    """Test recording a watch with default position_seconds (0)."""
    video = create_test_video(test_db, title="Test Video")
    
    response = client.post(
        f"/user/history/watched?user_id=user1&video_id={video.id}"
    )
    assert response.status_code == 200
    
    response = client.get("/user/history/watched?user_id=user1")
    data = response.json()
    assert data["videos"][0]["last_position_seconds"] == 0


def test_record_watch_missing_user_id(client, test_db):
    """Test recording a watch with missing user_id parameter."""
    video = create_test_video(test_db, title="Test Video")
    response = client.post(
        f"/user/history/watched?video_id={video.id}&position_seconds=0"
    )
    assert response.status_code == 422


def test_record_watch_missing_video_id(client):
    """Test recording a watch with missing video_id parameter."""
    response = client.post("/user/history/watched?user_id=user1&position_seconds=0")
    assert response.status_code == 422


def test_record_watch_negative_position(client, test_db):
    """Test recording a watch with negative position_seconds."""
    video = create_test_video(test_db, title="Test Video")
    response = client.post(
        f"/user/history/watched?user_id=user1&video_id={video.id}&position_seconds=-1"
    )
    assert response.status_code == 422


def test_get_watched_history_empty(client):
    """Test watched history for user with no watches."""
    response = client.get("/user/history/watched?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert data["videos"] == []


def test_get_watched_history_single_entry(client, test_db):
    """Test watched history with a single entry."""
    video = create_test_video(test_db, title="Watched Video", uploader_id=1)
    create_test_watch_history(test_db, user_id="user1", video_id=video.id, position_seconds=30)
    
    response = client.get("/user/history/watched?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video.id
    assert data["videos"][0]["title"] == "Watched Video"
    assert data["videos"][0]["last_position_seconds"] == 30


def test_get_watched_history_multiple_entries(client, test_db):
    """Test watched history with multiple entries."""
    video1 = create_test_video(test_db, title="Video 1", uploader_id=1)
    video2 = create_test_video(test_db, title="Video 2", uploader_id=2)
    video3 = create_test_video(test_db, title="Video 3", uploader_id=3)
    
    create_test_watch_history(test_db, user_id="user1", video_id=video1.id)
    create_test_watch_history(test_db, user_id="user1", video_id=video2.id)
    create_test_watch_history(test_db, user_id="user1", video_id=video3.id)
    
    response = client.get("/user/history/watched?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3


def test_get_watched_history_reverse_chronological(client, test_db):
    """Test that watched history is returned in reverse chronological order."""
    from datetime import datetime, timezone, timedelta
    from src.dashboard_service.models import WatchHistory
    
    video1 = create_test_video(test_db, title="Video 1", uploader_id=1)
    video2 = create_test_video(test_db, title="Video 2", uploader_id=2)
    video3 = create_test_video(test_db, title="Video 3", uploader_id=3)
    
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)
    
    watch1 = WatchHistory(user_id="user1", video_id=video1.id, last_watched_at=base_time)
    watch2 = WatchHistory(user_id="user1", video_id=video2.id, last_watched_at=base_time + timedelta(seconds=1))
    watch3 = WatchHistory(user_id="user1", video_id=video3.id, last_watched_at=base_time + timedelta(seconds=2))
    
    test_db.add_all([watch1, watch2, watch3])
    test_db.commit()
    
    response = client.get("/user/history/watched?user_id=user1")
    data = response.json()
    
    assert data["videos"][0]["id"] == video3.id
    assert data["videos"][1]["id"] == video2.id
    assert data["videos"][2]["id"] == video1.id


def test_get_watched_history_limit_default(client, test_db):
    """Test that watched history respects default limit of 20."""
    for i in range(25):
        video = create_test_video(test_db, title=f"Video {i}", uploader_id=i)
        create_test_watch_history(test_db, user_id="user1", video_id=video.id)
    
    response = client.get("/user/history/watched?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 20


def test_get_watched_history_limit_custom(client, test_db):
    """Test that watched history respects custom limit parameter."""
    for i in range(25):
        video = create_test_video(test_db, title=f"Video {i}", uploader_id=i)
        create_test_watch_history(test_db, user_id="user1", video_id=video.id)
    
    response = client.get("/user/history/watched?user_id=user1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 5


def test_get_watched_history_user_isolation(client, test_db):
    """Test that watched history is isolated per user."""
    video = create_test_video(test_db, title="Video")
    create_test_watch_history(test_db, user_id="user1", video_id=video.id)
    create_test_watch_history(test_db, user_id="user2", video_id=video.id)
    
    response = client.get("/user/history/watched?user_id=user1")
    data = response.json()
    assert len(data["videos"]) == 1


def test_get_watched_history_missing_video(client, test_db):
    """Test watched history excludes entries where video has been deleted."""
    video = create_test_video(test_db, title="Video")
    create_test_watch_history(test_db, user_id="user1", video_id="deleted_video_id")
    
    response = client.get("/user/history/watched?user_id=user1")
    data = response.json()
    assert len(data["videos"]) == 0


def test_get_watched_history_response_structure(client, test_db):
    """Test that watched history response has correct structure."""
    video = create_test_video(test_db, title="Test Video", uploader_id=1)
    create_test_watch_history(test_db, user_id="user1", video_id=video.id, position_seconds=45)
    
    response = client.get("/user/history/watched?user_id=user1")
    data = response.json()
    
    assert "user_id" in data
    assert "videos" in data
    assert isinstance(data["videos"], list)
    
    if data["videos"]:
        video_data = data["videos"][0]
        required_fields = {
            "id", "title", "description", "category", "tags",
            "thumbnail_url", "uploader_id", "views", "likes",
            "duration_seconds", "created_at",
            "last_watched_at", "last_position_seconds"
        }
        assert required_fields.issubset(video_data.keys())
