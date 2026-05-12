"""Unit tests for UserUpdate / UserResponse (no HTTP)."""

import os

os.environ["DATABASE_URL"] = "sqlite://"

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.user_prefs_and_accounts_service.main import UserResponse, UserUpdate  # noqa: E402


def test_user_update_all_fields_optional_default_none():
    m = UserUpdate()
    assert m.name is None and m.bio is None and m.avatar is None


def test_user_update_partial_payload():
    m = UserUpdate.model_validate({"bio": "only bio"})
    assert m.name is None
    assert m.bio == "only bio"
    assert m.avatar is None


def test_user_update_explicit_nulls():
    m = UserUpdate.model_validate({"name": None, "bio": None, "avatar": None})
    assert m.name is None and m.bio is None and m.avatar is None


def test_user_update_rejects_wrong_type_for_bio():
    with pytest.raises(ValidationError):
        UserUpdate.model_validate({"bio": 123})


def test_user_response_from_attributes():
    row = SimpleNamespace(
        id=1,
        name="N",
        email="n@example.com",
        role="user",
        bio="About me",
        avatar="https://x.test/a.png",
        is_active=True,
    )
    out = UserResponse.model_validate(row)
    assert out.model_dump() == {
        "id": 1,
        "name": "N",
        "email": "n@example.com",
        "role": "user",
        "bio": "About me",
        "avatar": "https://x.test/a.png",
        "is_active": True,
    }


def test_user_response_optional_bio_avatar_none():
    row = SimpleNamespace(
        id=2,
        name="Q",
        email="q@example.com",
        role="user",
        bio=None,
        avatar=None,
        is_active=True,
    )
    out = UserResponse.model_validate(row)
    assert out.bio is None and out.avatar is None