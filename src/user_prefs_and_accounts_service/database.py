"""SQLAlchemy engine, session factory, and database lifecycle for this service.

Creates tables on import and applies lightweight migrations for legacy schemas.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from .config import DATABASE_URL
from .models import Base

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_users_schema() -> None:
    """Add missing columns to ``users`` when upgrading an older database.

    Inspects the live ``users`` table and issues ``ALTER TABLE`` statements for
    columns required by the current ORM model (e.g. ``bio``, ``avatar``) if they
    are absent. No-op if the table does not exist or columns are already present.
    """
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    required_columns = {
        "bio": "VARCHAR",
        "avatar": "VARCHAR",
    }

    statements = []
    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            statements.append(
                text(f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}")
            )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(statement)


def init_db() -> None:
    """Create all ORM tables and align ``users`` schema with the current models."""
    Base.metadata.create_all(engine)
    _ensure_users_schema()


def get_db() -> Session:
    """FastAPI dependency that yields a database session and closes it after the request.

    Yields:
        sqlalchemy.orm.Session: Request-scoped session bound to ``engine``.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


init_db()
