import os
import time
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Example: postgresql://user:pass@host:5432/dbname")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_video_schema() -> None:
    inspector = inspect(engine)
    if "videos" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("videos")}
    required_columns = {
        "description": "VARCHAR NOT NULL DEFAULT ''",
        "category": "VARCHAR NOT NULL DEFAULT 'Education'",
        "tags": "VARCHAR NOT NULL DEFAULT ''",
        "thumbnail_url": "VARCHAR NOT NULL DEFAULT ''",
        "views": "INTEGER NOT NULL DEFAULT 0",
        "likes": "INTEGER NOT NULL DEFAULT 0",
        "duration_seconds": "INTEGER NOT NULL DEFAULT 0",
    }

    statements = []
    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            statements.append(text(f"ALTER TABLE videos ADD COLUMN {column_name} {column_definition}"))

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(statement)


def _ensure_video_transcript_schema() -> None:
    inspector = inspect(engine)
    if "video_transcripts" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("video_transcripts")}
    required_columns = {
        "status": "VARCHAR NOT NULL DEFAULT 'queued'",
        "error_message": "VARCHAR",
    }

    statements = []
    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            statements.append(
                text(f"ALTER TABLE video_transcripts ADD COLUMN {column_name} {column_definition}")
            )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(statement)


def _ensure_video_summary_schema() -> None:
    inspector = inspect(engine)
    if "video_summaries" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("video_summaries")}
    required_columns = {
        "status": "VARCHAR NOT NULL DEFAULT 'queued'",
        "summary": "VARCHAR",
        "source_kind": "VARCHAR NOT NULL DEFAULT 'video_metadata'",
        "provider": "VARCHAR",
        "error_message": "VARCHAR",
        "input_hash": "VARCHAR",
        "max_sentences": "INTEGER NOT NULL DEFAULT 3",
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "duration_ms": "INTEGER",
        "generated_at": "TIMESTAMP",
    }

    statements = []
    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            statements.append(text(f"ALTER TABLE video_summaries ADD COLUMN {column_name} {column_definition}"))

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(statement)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(max_retries: int = 30, retry_delay_seconds: int = 2):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_video_schema()
            _ensure_video_transcript_schema()
            _ensure_video_summary_schema()
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Database initialization failed after {max_retries} attempts"
    ) from last_error
