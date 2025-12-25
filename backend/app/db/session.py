"""Database session and engine configuration.

This module provides synchronous and asynchronous SQLAlchemy engines and
session factories. Using async is optional; for simplicity the core
application uses synchronous sessions via the ``SessionLocal`` factory.

Alembic migrations operate against the synchronous engine defined here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


settings = get_settings()

# Create synchronous engine and session factory
engine = create_engine(
    settings.database_url, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and closes it.

    Yields:
        A SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()