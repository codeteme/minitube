"""User profile, directory, and admin-style user management routes."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models import User, UserPreferences
from ..schemas import PublicUserResponse, UserResponse, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/profile/", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_active_user)) -> User:
    """Return the authenticated user's full profile."""
    return current_user


@router.get("/verify-token/")
def verify_token_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Lightweight check that the Bearer token is valid; returns user id, name, email, role."""
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
        },
    }


@router.get("/user/profile/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """Fetch a user by id; honors privacy when the viewer is not the same user.

    Raises:
        HTTPException: 404 if user not found or profile is private to others.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.id == user_id:
        return user
    prefs = (
        db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    )
    if prefs is not None and prefs.privacy == "private":
        raise HTTPException(status_code=404, detail="User is private")
    return user


@router.put("/user/profile/edit", response_model=UserResponse)
def update_user(
    update_user: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """Patch name, bio, and/or avatar URL for the current user only.

    Raises:
        HTTPException: 404 if the user row disappeared.
    """
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User does not exist")
    if update_user.name is not None:
        db_user.name = update_user.name
    if update_user.bio is not None:
        db_user.bio = update_user.bio
    if update_user.avatar is not None:
        db_user.avatar = update_user.avatar
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/users/{user_id}")
def delete(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete another user by id; self-deletion is rejected.

    Raises:
        HTTPException: 404 if target missing or if attempting to delete self.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User does not exist")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=404, detail="You cannot delete yourself!")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted!"}


@router.get("/users/", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> List[User]:
    """List every user (authenticated callers only)."""
    return db.query(User).all()


@router.get("/users/public/", response_model=List[PublicUserResponse])
def get_all_public_users(db: Session = Depends(get_db)) -> List[User]:
    """List active users with public fields only; no auth required."""
    return db.query(User).filter(User.is_active == True).all()  # noqa: E712


@router.get("/user/public/{user_id}", response_model=PublicUserResponse)
def get_public_user(user_id: int, db: Session = Depends(get_db)) -> User:
    """Return a minimal public profile for an active user.

    Raises:
        HTTPException: 404 if not found or inactive.
    """
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
