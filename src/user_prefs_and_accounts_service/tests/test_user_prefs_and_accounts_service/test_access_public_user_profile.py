import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before importing service module
os.environ["DATABASE_URL"] = "sqlite://"

from src.user_prefs_and_accounts_service.main import (  # noqa: E402
    Base,
    User,
    app,
    get_current_active_user,
    get_db,
    get_pwd_hash,
)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def seed_user(
    *,
    name: str,
    email: str,
    role: str,
    password: str,
    is_active: bool = True,
):
    db = TestingSessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            role=role,
            hashed_pwd=get_pwd_hash(password),
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def make_current_user_override(user_id: int):
    def _override():
        db = TestingSessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()

    return _override


def test_get_user_profile_success(client):
    requester = seed_user(
        name="Requester",
        email="requester@example.com",
        role="user",
        password="secret123",
        is_active=True,
    )
    target = seed_user(
        name="Target User",
        email="target@example.com",
        role="creator",
        password="secret123",
        is_active=True,
    )

    app.dependency_overrides[get_current_active_user] = make_current_user_override(requester.id)

    resp = client.get(f"/user/profile/{target.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == target.id
    assert body["name"] == "Target User"
    assert body["email"] == "target@example.com"
    assert body["role"] == "creator"
    assert body["is_active"] is True
    assert "hashed_pwd" not in body
    assert "password" not in body


def test_get_user_profile_not_found(client):
    requester = seed_user(
        name="Requester",
        email="requester2@example.com",
        role="user",
        password="secret123",
        is_active=True,
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(requester.id)

    resp = client.get("/user/profile/999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_get_user_profile_requires_auth(client):
    # No current-user override; endpoint should fail auth dependency
    resp = client.get("/user/profile/1")
    assert resp.status_code == 401