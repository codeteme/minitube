from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import declarative_base

# Separate Base so this model is never included in any service's create_all.
# The `users` table is owned and handled by user_prefs_and_accounts_service.
AdminBase = declarative_base()


class User(AdminBase):
    """Read/write access to the existing `users` table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    role = Column(String, nullable=False)
    hashed_pwd = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
