import os

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before importing main.py
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"

from src.user_prefs_and_accounts_service.main import (  # noqa: E402
    ALGORITHM,
    Base,
    SECRET_KEY,
    TOKEN_EXPIRES,
    User,
    app,
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


def test_login_success_returns_bearer_token(client):
    password = "secret123"
    email = "alice@example.com"
    seed_user(name="Alice", email=email, role="user", password=password, is_active=True)

    # OAuth2PasswordRequestForm expects form-encoded data
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert body["access_token"]

    payload = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == email
    assert "exp" in payload


def test_login_wrong_password_returns_401(client):
    seed_user(
        name="Bob",
        email="bob@example.com",
        role="user",
        password="correct-password",
        is_active=True,
    )

    resp = client.post(
        "/auth/login",
        data={"username": "bob@example.com", "password": "wrong-password"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
    assert resp.headers["www-authenticate"] == "Bearer"


def test_login_unknown_user_returns_401(client):
    resp = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "secret123"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
    assert resp.headers["www-authenticate"] == "Bearer"


def test_login_inactive_user_returns_401(client):
    seed_user(
        name="Carol",
        email="carol@example.com",
        role="user",
        password="secret123",
        is_active=False,
    )

    resp = client.post(
        "/auth/login",
        data={"username": "carol@example.com", "password": "secret123"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
    assert resp.headers["www-authenticate"] == "Bearer"


def test_login_missing_form_fields_returns_422(client):
    resp = client.post("/auth/login", data={"username": "alice@example.com"})
    assert resp.status_code == 422