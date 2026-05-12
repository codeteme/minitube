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
    bio: str | None = None,
    avatar: str | None = None,
):
    db = TestingSessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            role=role,
            hashed_pwd=get_pwd_hash(password),
            is_active=is_active,
            bio=bio,
            avatar=avatar,
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


def test_update_own_profile_full_user_update(client):
    current = seed_user(
        name="Old Name",
        email="user@example.com",
        role="user",
        password="secret123",
        bio="Old bio",
        avatar="https://example.com/old.png",
    )

    db = TestingSessionLocal()
    try:
        original_hashed_pwd = db.query(User).filter(User.id == current.id).first().hashed_pwd
    finally:
        db.close()

    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    payload = {
        "name": "New Name",
        "bio": "New bio",
        "avatar": "https://example.com/new.png",
    }

    resp = client.put("/user/profile/edit", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == current.id
    assert body["name"] == payload["name"]
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"
    assert body["bio"] == payload["bio"]
    assert body["avatar"] == payload["avatar"]
    assert body["is_active"] is True
    assert "hashed_pwd" not in body
    assert "password" not in body

    db = TestingSessionLocal()
    try:
        updated = db.query(User).filter(User.id == current.id).first()
        assert updated is not None
        assert updated.name == payload["name"]
        assert updated.bio == payload["bio"]
        assert updated.avatar == payload["avatar"]
        assert updated.email == "user@example.com"
        assert updated.role == "user"
        assert updated.hashed_pwd == original_hashed_pwd
    finally:
        db.close()


def test_update_own_profile_partial_bio_only(client):
    current = seed_user(
        name="Pat",
        email="pat@example.com",
        role="user",
        password="secret123",
        bio="Original bio",
        avatar="https://example.com/face.png",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.put("/user/profile/edit", json={"bio": "Only bio changed"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Pat"
    assert body["bio"] == "Only bio changed"
    assert body["avatar"] == "https://example.com/face.png"

    db = TestingSessionLocal()
    try:
        row = db.query(User).filter(User.id == current.id).first()
        assert row.name == "Pat"
        assert row.bio == "Only bio changed"
        assert row.avatar == "https://example.com/face.png"
    finally:
        db.close()


def test_update_own_profile_empty_body_leaves_row_unchanged(client):
    current = seed_user(
        name="Sam",
        email="sam@example.com",
        role="admin",
        password="secret123",
        bio="Keeps",
        avatar="https://example.com/a.png",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.put("/user/profile/edit", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Sam"
    assert body["bio"] == "Keeps"
    assert body["avatar"] == "https://example.com/a.png"


def test_update_own_profile_extra_keys_ignored(client):
    """UserUpdate only has name/bio/avatar; email/role must not change from extras."""
    current = seed_user(
        name="Eve",
        email="eve@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.put(
        "/user/profile/edit",
        json={
            "name": "Eve Updated",
            "email": "hacker@example.com",
            "role": "admin",
            "password": "nope",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["email"] == "eve@example.com"
    assert resp.json()["role"] == "user"

    db = TestingSessionLocal()
    try:
        row = db.query(User).filter(User.id == current.id).first()
        assert row.email == "eve@example.com"
        assert row.role == "user"
    finally:
        db.close()


def test_update_own_profile_null_bio_does_not_clear_existing(client):
    """None / null means \"omit patch\" for optional UserUpdate fields."""
    current = seed_user(
        name="NoClear",
        email="noclear@example.com",
        role="user",
        password="secret123",
        bio="Still here",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.put("/user/profile/edit", json={"name": "Renamed", "bio": None})

    assert resp.status_code == 200
    db = TestingSessionLocal()
    try:
        row = db.query(User).filter(User.id == current.id).first()
        assert row.name == "Renamed"
        assert row.bio == "Still here"
    finally:
        db.close()


def test_get_profile_returns_bio_and_avatar(client):
    current = seed_user(
        name="Profile Reader",
        email="reader@example.com",
        role="user",
        password="secret123",
        bio="Hello",
        avatar="https://example.com/p.png",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.get("/profile/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "Hello"
    assert body["avatar"] == "https://example.com/p.png"


def test_update_own_profile_user_not_found(client):
    class MissingUser:
        id = 999999
        is_active = True

    app.dependency_overrides[get_current_active_user] = lambda: MissingUser()

    resp = client.put("/user/profile/edit", json={"name": "Any"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "User does not exist"


def test_update_own_profile_requires_auth(client):
    resp = client.put("/user/profile/edit", json={"name": "No Auth"})

    assert resp.status_code == 401


def test_update_own_profile_invalid_payload_returns_422(client):
    current = seed_user(
        name="User",
        email="user@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(current.id)

    resp = client.put("/user/profile/edit", json={"bio": ["not", "a", "string"]})

    assert resp.status_code == 422