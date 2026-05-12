"""Pydantic request/response models and shared validation for the HTTP API."""
import re
from typing import List, Optional

from pydantic import BaseModel, field_validator
from .config import PASSWORD_MIN_LENGTH


def validate_password_strength(password: str) -> str:
    """Enforce minimum length, at least one letter, and at least one digit.

    Args:
        password: Plain-text password from registration or reset flows.

    Returns:
        The same password string if all rules pass.

    Raises:
        ValueError: If any strength rule fails.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must include at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must include at least one number.")
    return password


class UserCreate(BaseModel):
    """Payload for registering a new user."""

    name: str
    email: str
    role: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Apply :func:`validate_password_strength` to ``password``."""
        return validate_password_strength(value)


class UserUpdate(BaseModel):
    """Partial profile update for the authenticated user (name, bio, avatar URL)."""

    name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    """Full user profile returned to clients that are allowed to see it."""

    id: int
    name: str
    email: str
    role: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool

    class Config:
        """Enable construction from ORM attributes (``from_attributes``)."""

        from_attributes = True


class PublicUserResponse(BaseModel):
    """Limited user fields exposed in public listings and anonymous profile views."""

    id: int
    name: str
    avatar: Optional[str] = None

    class Config:
        """Enable construction from ORM attributes (``from_attributes``)."""

        from_attributes = True


class UserLogin(BaseModel):
    """JSON login body (alternative to OAuth2 form login in some clients)."""

    email: str
    password: str


class Token(BaseModel):
    """OAuth2-style access token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Claims extracted from a validated JWT (subject email)."""

    email: Optional[str] = None


class UserPreferencesResponse(BaseModel):
    """Current preferences row for a user."""

    user_id: int
    privacy: str
    notifications: bool
    ui_theme: str

    class Config:
        """Enable construction from ORM attributes (``from_attributes``)."""

        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """Partial update for privacy, notifications, and theme."""

    privacy: Optional[str] = None
    notifications: Optional[bool] = None
    ui_theme: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Email address submitted to start the forgot-password flow."""

    email: str


class PasswordResetConfirm(BaseModel):
    """Reset token plus the new password to set after verification."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Apply :func:`validate_password_strength` to ``new_password``."""
        return validate_password_strength(value)
