from io import BytesIO
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.video_crud_service.main import app
from src.video_crud_service.database import Base
from src.video_crud_service.videos import get_db, get_current_user_id
from src.video_crud_service.models import Video


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    # Use check_same_thread=False to allow access from multiple threads (needed for TestClient)
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
    app.dependency_overrides[get_current_user_id] = lambda: 1
    db_session = SessionLocal()
    yield db_session
    db_session.close()
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(test_db):
    """FastAPI TestClient using test database."""
    return TestClient(app)


@pytest.fixture
def sample_video_file():
    """Create a minimal video file for testing."""
    # Minimal MP4 header (valid but empty)
    mp4_header = bytes.fromhex(
        "0000002066747970697361706d00000000697361766d69736f6d69736f326d7031323900000000"
    )
    return BytesIO(mp4_header)


def create_test_video(db, title="Test Video", uploader_id=1, path="/tmp/test.mp4", views=0):
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
        path=path,
        views=views,
        likes=0,
        duration_seconds=60,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
