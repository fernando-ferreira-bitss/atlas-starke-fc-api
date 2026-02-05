"""Database dependency for FastAPI."""

from typing import Generator

from sqlalchemy.orm import Session

from starke.infrastructure.database.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
