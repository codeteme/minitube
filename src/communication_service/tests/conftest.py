import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before importing application modules that initialize DB engine.
os.environ["DATABASE_URL"] = "sqlite://"

from src.communication_service.main import (  # noqa: E402
    app,
    get_db,
    chat_rooms,
    chat_history,
    direct_chat_rooms,
    direct_chat_history,
    notification_stream_clients,
    direct_room_active_users,
)
from src.video_crud_service.database import Base  # noqa: E402


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

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
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_in_memory_state():
    chat_rooms.clear()
    chat_history.clear()
    direct_chat_rooms.clear()
    direct_chat_history.clear()
    notification_stream_clients.clear()
    direct_room_active_users.clear()
    yield
    chat_rooms.clear()
    chat_history.clear()
    direct_chat_rooms.clear()
    direct_chat_history.clear()
    notification_stream_clients.clear()
    direct_room_active_users.clear()
