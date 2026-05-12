from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.dashboard_service.main import app
from src.video_crud_service.database import Base
from src.dashboard_service.main import get_db
from src.video_crud_service.models import Video, VideoTranscript
from src.dashboard_service.models import SearchHistory, WatchHistory, Subscription


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    db_session = SessionLocal()
    yield db_session
    db_session.close()
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(test_db):
    """FastAPI TestClient using test database."""
    return TestClient(app)


def create_test_video(db, title="Test Video", uploader_id=1, views=0):
    """Helper to create a video in the database."""
    video = Video(
        id=str(uuid4()),
        title=title,
        description="Test description",
        category="Education",
        tags="test,python",
        thumbnail_url="/videos/test/thumbnail",
        uploader_id=uploader_id,
        original_filename="test.mp4",
        saved_filename="test_saved.mp4",
        content_type="video/mp4",
        size=1024,
        path="/tmp/test.mp4",
        views=views,
        likes=0,
        duration_seconds=60,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def create_test_subscription(db, subscriber_user_id="user1", channel_user_id="channel1"):
    """Helper to create a subscription in the database."""
    subscription = Subscription(
        subscriber_user_id=subscriber_user_id,
        channel_user_id=channel_user_id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def create_test_search_history(db, user_id="user1", query="test query"):
    """Helper to create a search history entry."""
    history = SearchHistory(
        user_id=user_id,
        query=query,
        searched_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def create_test_watch_history(db, user_id="user1", video_id="video1", position_seconds=0):
    """Helper to create a watch history entry."""
    watch = WatchHistory(
        user_id=user_id,
        video_id=video_id,
        last_position_seconds=position_seconds,
        last_watched_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def create_test_transcript(
    db,
    video_id: str,
    transcript_text: str,
    source: str = "asr",
    language: str | None = "en",
    status: str = "ready",
):
    transcript = VideoTranscript(
        video_id=video_id,
        transcript_text=transcript_text,
        source=source,
        status=status,
        language=language,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript
