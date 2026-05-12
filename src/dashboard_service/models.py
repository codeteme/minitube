from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base

from src.video_crud_service.database import Base

# Separate base so User is never passed to video_crud's create_all.
# The `users` table is owned by user_prefs_and_accounts_service.
DashboardExternalBase = declarative_base()


class User(DashboardExternalBase):
    """Read-only mirror of the `users` table for search queries."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    query = Column(String, nullable=False)
    searched_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    video_id = Column(String, nullable=False)
    last_position_seconds = Column(Integer, nullable=False, default=0)
    last_watched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Ensure a user can only have one watch history entry per video
    __table_args__ = (UniqueConstraint("user_id", "video_id", name="uq_watch_history_user_video"),)


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscriber_user_id = Column(String, primary_key=True, nullable=False, index=True)
    channel_user_id = Column(String, primary_key=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
