from datetime import datetime, timezone, timedelta

from src.video_crud_service.models import Video

from .conftest import create_test_video, create_test_watch_history


def test_recommend_empty_database(client):
    """Test recommendations when database is empty."""
    response = client.get("/dashboard/recommend")
    assert response.status_code == 200
    data = response.json()
    assert data["videos"] == []


def test_recommend_single_video(client, test_db):
    """Test recommendations with a single video."""
    video = create_test_video(test_db, title="Test Video")
    
    response = client.get("/dashboard/recommend")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video.id
    assert data["videos"][0]["title"] == "Test Video"


def test_recommend_multiple_videos(client, test_db):
    """Test recommendations with multiple videos."""
    video1 = create_test_video(test_db, title="Video 1", uploader_id=1)
    video2 = create_test_video(test_db, title="Video 2", uploader_id=2)
    video3 = create_test_video(test_db, title="Video 3", uploader_id=3)
    
    response = client.get("/dashboard/recommend")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3


def test_recommend_reverse_chronological_order(client, test_db):
    """Test that recommendations are in reverse chronological order (newest first)."""
    from datetime import datetime, timezone, timedelta
    from src.video_crud_service.models import Video
    
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)
    
    video1 = Video(
        id="video1",
        title="Oldest Video",
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
        title="Middle Video",
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
    video3 = Video(
        id="video3",
        title="Newest Video",
        description="Test",
        category="Test",
        tags="test",
        thumbnail_url="/thumb3",
        uploader_id=1,
        original_filename="test3.mp4",
        saved_filename="test3_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/test3.mp4",
        views=0,
        likes=0,
        duration_seconds=60,
        created_at=base_time + timedelta(seconds=2),
    )
    
    test_db.add_all([video1, video2, video3])
    test_db.commit()
    
    response = client.get("/dashboard/recommend")
    data = response.json()
    
    assert len(data["videos"]) == 3
    assert data["videos"][0]["id"] == "video3"
    assert data["videos"][1]["id"] == "video2"
    assert data["videos"][2]["id"] == "video1"


def test_recommend_response_structure(client, test_db):
    """Test that recommend response has correct structure."""
    video = create_test_video(test_db, title="Test Video", uploader_id=1)
    
    response = client.get("/dashboard/recommend")
    data = response.json()
    
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


def test_recommend_personalized_prefers_matching_tags(client, test_db):
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)

    watched = Video(
        id="watched-music",
        title="Watched music",
        description="history anchor",
        category="Music",
        tags="music,concert",
        thumbnail_url="/thumb-w",
        uploader_id=1,
        original_filename="w.mp4",
        saved_filename="w_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/w.mp4",
        views=5,
        likes=1,
        duration_seconds=60,
        created_at=base_time,
    )
    match_candidate = Video(
        id="candidate-music",
        title="Recommended music",
        description="similar topic",
        category="Music",
        tags="music,live-stream",
        thumbnail_url="/thumb-m",
        uploader_id=2,
        original_filename="m.mp4",
        saved_filename="m_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/m.mp4",
        views=1,
        likes=0,
        duration_seconds=60,
        created_at=base_time + timedelta(seconds=10),
    )
    non_match_candidate = Video(
        id="candidate-sports",
        title="Sports update",
        description="different topic",
        category="Sports",
        tags="sports",
        thumbnail_url="/thumb-s",
        uploader_id=3,
        original_filename="s.mp4",
        saved_filename="s_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/s.mp4",
        views=100,
        likes=10,
        duration_seconds=60,
        created_at=base_time + timedelta(seconds=20),
    )

    test_db.add_all([watched, match_candidate, non_match_candidate])
    test_db.commit()
    create_test_watch_history(test_db, user_id="u-1", video_id="watched-music", position_seconds=240)

    response = client.get("/dashboard/recommend?user_id=u-1")
    assert response.status_code == 200
    data = response.json()
    ids = [v["id"] for v in data["videos"]]

    assert "watched-music" not in ids
    assert ids[0] == "candidate-music"
