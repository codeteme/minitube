import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before importing service module
os.environ["DATABASE_URL"] = "sqlite://"

from src.user_prefs_and_accounts_service.main import (
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


def seed_user(name: str, email: str, role: str, password: str) -> int:
    db = TestingSessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            role=role,
            hashed_pwd=get_pwd_hash(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
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


def test_delete_user_success(client):
    admin_id = seed_user("Admin", "admin@example.com", "admin", "secret123")
    victim_id = seed_user("Victim", "victim@example.com", "user", "secret123")

    app.dependency_overrides[get_current_active_user] = make_current_user_override(admin_id)

    r = client.delete(f"/users/{victim_id}")

    assert r.status_code == 200
    assert r.json() == {"message": "User deleted!"}

    db = TestingSessionLocal()
    try:
        deleted = db.query(User).filter(User.id == victim_id).first()
        admin = db.query(User).filter(User.id == admin_id).first()
        assert deleted is None
        assert admin is not None
    finally:
        db.close()


def test_delete_user_not_found(client):
    admin_id = seed_user("Admin", "admin2@example.com", "admin", "secret123")
    app.dependency_overrides[get_current_active_user] = make_current_user_override(admin_id)

    r = client.delete("/users/999999")

    assert r.status_code == 404
    assert r.json()["detail"] == "User does not exist"


def test_delete_user_cannot_delete_self(client):
    user_id = seed_user("Self", "self@example.com", "user", "secret123")
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user_id)

    r = client.delete(f"/users/{user_id}")

    assert r.status_code == 404
    assert r.json()["detail"] == "You cannot delete yourself!"

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
    finally:
        db.close()


def test_delete_user_requires_auth(client):
    # No get_current_active_user override -> should fail auth
    r = client.delete("/users/1")
    assert r.status_code == 401