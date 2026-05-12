from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from src.video_crud_service.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    recipient_user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    actor_user_id = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
