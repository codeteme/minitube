from .conftest import create_test_video, create_test_subscription


def test_subscriptions_feed_empty(client):
    """Test subscriptions feed for user with no subscriptions."""
    response = client.get("/subscriptions/feed?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert data["videos"] == []


def test_subscriptions_feed_single_subscription(client, test_db):
    """Test subscriptions feed with a single subscription."""
    video = create_test_video(test_db, title="Channel Video", uploader_id=1)
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video.id
    assert data["videos"][0]["title"] == "Channel Video"


def test_subscriptions_feed_multiple_subscriptions(client, test_db):
    """Test subscriptions feed with multiple subscriptions."""
    video1 = create_test_video(test_db, title="Channel 1 Video", uploader_id=1)
    video2 = create_test_video(test_db, title="Channel 2 Video", uploader_id=2)
    video3 = create_test_video(test_db, title="Channel 3 Video", uploader_id=3)
    
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="2")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 2
    video_ids = {v["id"] for v in data["videos"]}
    assert video1.id in video_ids
    assert video2.id in video_ids
    assert video3.id not in video_ids


def test_subscriptions_feed_reverse_chronological(client, test_db):
    """Test that subscriptions feed is in reverse chronological order."""
    from datetime import datetime, timezone, timedelta
    from src.video_crud_service.models import Video
    
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)
    
    video1 = Video(
        id="video1",
        title="First Video",
        description="Test",
        category="Test",
        tags="test",
        thumbnail_url="/thumb1",
        uploader_id=1,
        original_filename="test1.mp4",
        saved_filename="test1_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/test1.mp4",
        views=0,
        likes=0,
        duration_seconds=60,
        created_at=base_time,
    )
    video2 = Video(
        id="video2",
        title="Second Video",
        description="Test",
        category="Test",
        tags="test",
        thumbnail_url="/thumb2",
        uploader_id=1,
        original_filename="test2.mp4",
        saved_filename="test2_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/test2.mp4",
        views=0,
        likes=0,
        duration_seconds=60,
        created_at=base_time + timedelta(seconds=1),
    )
    
    test_db.add_all([video1, video2])
    test_db.commit()
    
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    data = response.json()
    
    assert len(data["videos"]) == 2
    assert data["videos"][0]["id"] == "video2"
    assert data["videos"][1]["id"] == "video1"


def test_subscriptions_feed_limit_default(client, test_db):
    """Test that subscriptions feed respects default limit of 20."""
    # Create 25 videos all from uploader_id=1 (but with different timestamps)
    from datetime import datetime, timezone, timedelta
    from src.video_crud_service.models import Video
    
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(25):
        video = Video(
            id=f"video{i}",
            title=f"Video {i}",
            description="Test",
            category="Test",
            tags="test",
            thumbnail_url=f"/thumb{i}",
            uploader_id=1,
            original_filename=f"test{i}.mp4",
            saved_filename=f"test{i}_saved.mp4",
            content_type="video/mp4",
            size=1024,
            path=f"/tmp/test{i}.mp4",
            views=0,
            likes=0,
            duration_seconds=60,
            created_at=base_time + timedelta(seconds=i),
        )
        test_db.add(video)
    test_db.commit()
    
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 20


def test_subscriptions_feed_limit_custom(client, test_db):
    """Test that subscriptions feed respects custom limit parameter."""
    for i in range(25):
        video = create_test_video(test_db, title=f"Video {i}", uploader_id=1)
    
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    
    response = client.get("/subscriptions/feed?user_id=user1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 5


def test_subscriptions_feed_missing_user_id(client):
    """Test subscriptions feed with missing user_id parameter."""
    response = client.get("/subscriptions/feed")
    assert response.status_code == 422


def test_subscriptions_feed_limit_max_100(client, test_db):
    """Test that limit parameter is capped at 100."""
    response = client.get("/subscriptions/feed?user_id=user1&limit=101")
    assert response.status_code == 422


def test_subscriptions_feed_limit_min_1(client, test_db):
    """Test that limit parameter must be at least 1."""
    response = client.get("/subscriptions/feed?user_id=user1&limit=0")
    assert response.status_code == 422


def test_subscriptions_feed_user_isolation(client, test_db):
    """Test that subscriptions feed is isolated per user."""
    video1 = create_test_video(test_db, title="Video 1", uploader_id=1)
    video2 = create_test_video(test_db, title="Video 2", uploader_id=2)
    
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    create_test_subscription(test_db, subscriber_user_id="user2", channel_user_id="2")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video1.id


def test_subscriptions_feed_response_structure(client, test_db):
    """Test that subscriptions feed response has correct structure."""
    video = create_test_video(test_db, title="Test Video", uploader_id=1)
    create_test_subscription(test_db, subscriber_user_id="user1", channel_user_id="1")
    
    response = client.get("/subscriptions/feed?user_id=user1")
    data = response.json()
    
    assert "user_id" in data
    assert "videos" in data
    assert isinstance(data["videos"], list)
    
    if data["videos"]:
        video_data = data["videos"][0]
        required_fields = {
            "id", "title", "description", "category", "tags",
            "thumbnail_url", "uploader_id", "views", "likes",
            "duration_seconds", "created_at"
        }
        assert required_fields.issubset(video_data.keys())
