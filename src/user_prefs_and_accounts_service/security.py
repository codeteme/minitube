"""Password hashing, JWT access and reset tokens, and OAuth2 bearer extraction."""
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from .config import ALGORITHM, SECRET_KEY
from .schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_pwd(plain_pwd: str, hashed_pwd: str) -> bool:
    """Return whether ``plain_pwd`` matches the stored bcrypt hash."""
    return pwd_context.verify(plain_pwd, hashed_pwd)


def get_pwd_hash(password: str) -> str:
    """Hash ``password`` for persistence (bcrypt via passlib)."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Build a signed JWT for API access with optional custom lifetime.

    Args:
        data: Claims to embed; typically includes ``sub`` (user email).
        expires_delta: If set, ``exp`` is now plus this delta; else 15 minutes.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT marked as type ``reset`` for password recovery.

    Args:
        email: User email stored in the ``sub`` claim.

    Returns:
        Encoded JWT; lifetime from :data:`~.config.RESET_TOKEN_EXPIRES` minutes.
    """
    from .config import RESET_TOKEN_EXPIRES

    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRES)
    to_encode = {"sub": email, "exp": expire, "type": "reset"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Decode a reset token and return the email if valid and typed as reset.

    Args:
        token: JWT from the reset link.

    Returns:
        Email string, or ``None`` if invalid, wrong type, or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def verify_token(token: str) -> TokenData:
    """Validate an access JWT and return the subject email.

    Args:
        token: Bearer token string.

    Returns:
        :class:`~.schemas.TokenData` with ``email`` set from ``sub``.

    Raises:
        HTTPException: 401 if the token is missing ``sub`` or fails verification.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(email=email)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
