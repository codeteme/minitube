import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-avatar-tests"
os.environ["ALGORITHM"] = "HS256"

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


def _avatar_routes_mounted() -> bool:
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path == "/user/profile/avatar" and "POST" in methods:
            return True
    return False


if not _avatar_routes_mounted():
    from src.user_prefs_and_accounts_service.avatars import (  # noqa: E402
        router as avatars_router,
    )

    app.include_router(avatars_router)


from src.user_prefs_and_accounts_service.avatars import MAX_AVATAR_BYTES  # noqa: E402

MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0bIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xcc\x59\xe7"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def test_upload_avatar_success(client, tmp_path):
    user = seed_user(
        name="Uploader",
        email="up@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user.id)

    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.post(
            "/user/profile/avatar",
            files={"file": ("face.png", MINIMAL_PNG, "image/png")},
        )

    assert r.status_code == 200
    body = r.json()
    saved_name = f"{user.id}.png"
    expected_avatar = f"/user/profile/avatar/file/{saved_name}"
    assert body["avatar"] == expected_avatar
    assert body["id"] == user.id

    on_disk = tmp_path / str(user.id) / saved_name
    assert on_disk.is_file()
    assert on_disk.read_bytes() == MINIMAL_PNG

    db = TestingSessionLocal()
    try:
        row = db.query(User).filter(User.id == user.id).first()
        assert row.avatar == expected_avatar
    finally:
        db.close()


def test_get_avatar_file_after_upload(client, tmp_path):
    user = seed_user(
        name="Getter",
        email="get@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user.id)

    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        up = client.post(
            "/user/profile/avatar",
            files={"file": ("a.webp", MINIMAL_PNG, "image/png")},
        )
    assert up.status_code == 200
    saved_name = f"{user.id}.webp"
    assert up.json()["avatar"] == f"/user/profile/avatar/file/{saved_name}"

    serve_path = f"/user/profile/avatar/file/{user.id}/{saved_name}"
    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        got = client.get(serve_path)

    assert got.status_code == 200
    assert got.content == MINIMAL_PNG
    assert got.headers["content-type"].startswith("image/")


def test_upload_unsupported_file_type(client, tmp_path):
    user = seed_user(
        name="Bad",
        email="bad@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user.id)

    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.post(
            "/user/profile/avatar",
            files={"file": ("x.txt", b"not-an-image", "text/plain")},
        )

    assert r.status_code == 400
    assert r.json()["detail"] == "Unsupported file type"


def test_upload_too_large(client, tmp_path):
    user = seed_user(
        name="Big",
        email="big@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user.id)
    payload = b"x" * (MAX_AVATAR_BYTES + 1)

    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.post(
            "/user/profile/avatar",
            files={"file": ("big.png", payload, "image/png")},
        )

    assert r.status_code == 400
    assert r.json()["detail"] == "Avatar too large"


def test_upload_requires_auth(client, tmp_path):
    seed_user(
        name="Solo",
        email="solo@example.com",
        role="user",
        password="secret123",
    )

    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.post(
            "/user/profile/avatar",
            files={"file": ("a.png", MINIMAL_PNG, "image/png")},
        )

    assert r.status_code == 401


def test_get_avatar_not_found(client, tmp_path):
    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.get("/user/profile/avatar/file/99999/99999.png")

    assert r.status_code == 404
    assert r.json()["detail"] == "Avatar not found"


def test_get_avatar_uses_basename_for_filename(client, tmp_path):
    user = seed_user(
        name="Traverse",
        email="tr@example.com",
        role="user",
        password="secret123",
    )
    app.dependency_overrides[get_current_active_user] = make_current_user_override(user.id)

    saved_name = f"{user.id}.png"
    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        client.post(
            "/user/profile/avatar",
            files={"file": ("z.png", MINIMAL_PNG, "image/png")},
        )

    evil = f"../{user.id}/{saved_name}"
    with patch("src.user_prefs_and_accounts_service.avatars.AVATAR_DIR", tmp_path):
        r = client.get(f"/user/profile/avatar/file/{user.id}/{evil}")

    assert r.status_code == 200
    assert r.content == MINIMAL_PNG