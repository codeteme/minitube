import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# set before importing app module
os.environ["DATABASE_URL"] = "sqlite://"

from src.user_prefs_and_accounts_service.main import Base, User, app, get_db

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
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_user_success(client):
    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "role": "user",
        "password": "secret123",
    }

    r = client.post("/auth/register", json=payload)

    assert r.status_code == 200
    body = r.json()
    assert body["name"] == payload["name"]
    assert body["email"] == payload["email"]
    assert body["role"] == payload["role"]
    assert body["is_active"] is True
    assert "id" in body
    assert "password" not in body
    assert "hashed_pwd" not in body

    db = TestingSessionLocal()
    try:
        db_user = db.query(User).filter(User.email == payload["email"]).first()
        assert db_user is not None
        assert db_user.hashed_pwd != payload["password"]
    finally:
        db.close()


def test_register_user_duplicate_email_returns_404(client):
    payload = {
        "name": "Bob",
        "email": "bob@example.com",
        "role": "user",
        "password": "secret123",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 404
    assert second.json()["detail"] == "User already created!"


def test_register_user_invalid_payload_returns_422(client):
    payload = {
        "name": "NoPassword",
        "email": "nopassword@example.com",
        "role": "user",
    }

    r = client.post("/auth/register", json=payload)

    assert r.status_code == 422


def test_register_user_weak_password_returns_422(client):
    payload = {
        "name": "WeakPasswordUser",
        "email": "weak@example.com",
        "role": "user",
        "password": "password",
    }

    r = client.post("/auth/register", json=payload)

    assert r.status_code == 422
    assert "number" in str(r.json()).lower()
