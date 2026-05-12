"""FastAPI dependencies for resolving the current user from a Bearer token."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import oauth2_scheme, verify_token


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Load the :class:`~.models.User` matching the JWT subject (email).

    Args:
        token: Bearer token from ``Authorization`` header (via ``oauth2_scheme``).
        db: Database session.

    Returns:
        The authenticated user row.

    Raises:
        HTTPException: 401 if no user exists for the token's email.
    """
    token_data = verify_token(token)
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Same as :func:`get_current_user`, but rejects inactive accounts.

    Args:
        current_user: User resolved by :func:`get_current_user`.

    Returns:
        The user if ``is_active`` is true.

    Raises:
        HTTPException: 404 if the account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=404,
            detail="Incative User",
        )
    return current_user
