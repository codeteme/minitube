"""Authentication routes: register, login, forgot password, and reset password."""
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import TOKEN_EXPIRES
from ..database import get_db
from ..email_service import send_reset_email
from ..models import User
from ..schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserResponse,
)
from ..security import (
    create_access_token,
    create_password_reset_token,
    get_pwd_hash,
    verify_pwd,
    verify_password_reset_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new user with a hashed password if email and name are available.

    Raises:
        HTTPException: 404 if email exists; 400 if display name is taken.
    """
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=404, detail="User already created!")
    if db.query(User).filter(User.name == user.name).first():
        raise HTTPException(status_code=400, detail="That username is already taken.")

    hashed_password = get_pwd_hash(user.password)
    db_user = User(
        name=user.name,
        email=user.email,
        role=user.role,
        hashed_pwd=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login/", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> dict:
    """OAuth2 password flow: validate credentials and return a JWT access token.

    ``username`` in the form is treated as the user's email.

    Raises:
        HTTPException: 401 for bad password, unknown user, or inactive account.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_pwd(form_data.password, user.hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=TOKEN_EXPIRES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Queue a reset email for active users; always returns the same generic message.

    Avoids leaking whether an email is registered.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user and user.is_active:
        token = create_password_reset_token(user.email)
        background_tasks.add_task(send_reset_email, user.email, token)
    return {"message": "If that email is in our system, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict:
    """Set a new password when the reset token is valid and the user is active.

    Raises:
        HTTPException: 400 for invalid/expired token; 404 if user missing or inactive.
    """
    email = verify_password_reset_token(request.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.hashed_pwd = get_pwd_hash(request.new_password)
    db.commit()
    return {"message": "Password has been reset successfully"}
