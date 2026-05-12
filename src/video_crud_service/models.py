from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from .database import Base


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    category = Column(String, nullable=False, default="Education")
    tags = Column(String, nullable=False, default="")
    thumbnail_url = Column(String, nullable=False, default="")
    uploader_id = Column(Integer, nullable=False)
    original_filename = Column(String, nullable=False)
    saved_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    path = Column(String, nullable=False)
    views = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class VideoTranscript(Base):
    __tablename__ = "video_transcripts"

    video_id = Column(String, primary_key=True, index=True)
    transcript_text = Column(String, nullable=False, default="")
    source = Column(String, nullable=False, default="asr")
    status = Column(String, nullable=False, default="queued")
    error_message = Column(String, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoSummary(Base):
    __tablename__ = "video_summaries"

    video_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="queued")
    summary = Column(String, nullable=True)
    source_kind = Column(String, nullable=False, default="video_metadata")
    provider = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    input_hash = Column(String, nullable=True)
    max_sentences = Column(Integer, nullable=False, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoTag(Base):
    __tablename__ = "video_tags"

    video_id = Column(String, primary_key=True, index=True)
    tag = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TagTaxonomy(Base):
    __tablename__ = "tag_taxonomy"

    canonical_tag = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="general")
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class TagAlias(Base):
    __tablename__ = "tag_aliases"

    alias = Column(String, primary_key=True)
    canonical_tag = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
