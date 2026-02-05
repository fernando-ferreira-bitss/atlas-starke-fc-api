"""Database base configuration and session management."""

import logging
import time
from contextlib import contextmanager
from typing import Callable, Generator, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from starke.core.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Create engine with connection resilience settings
settings = get_settings()
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Check connection health before using
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_timeout=30,  # Timeout to get connection from pool
    pool_size=5,  # Number of connections in the pool
    max_overflow=10,  # Max connections beyond pool_size
    connect_args={
        "keepalives": 1,  # Enable TCP keepalives
        "keepalives_idle": 30,  # Seconds before sending keepalive
        "keepalives_interval": 10,  # Seconds between keepalives
        "keepalives_count": 5,  # Max keepalive failures before disconnect
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=60000 -c lock_timeout=30000",  # 60s query timeout, 30s lock timeout
    },
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def execute_with_retry(
    session: Session,
    operation: Callable[[], T],
    max_retries: int = 3,
    retry_delay: float = 2.0,
    operation_name: str = "database operation"
) -> T:
    """
    Execute a database operation with automatic retry on connection errors.

    Args:
        session: SQLAlchemy session
        operation: Callable that performs the database operation
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        operation_name: Name for logging purposes

    Returns:
        Result of the operation

    Raises:
        Exception: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry {attempt}/{max_retries} for {operation_name}...")
                time.sleep(retry_delay * attempt)  # Exponential backoff

                # Try to recover the session
                try:
                    session.rollback()
                    session.execute(text("SELECT 1"))
                    logger.info("Session recovered successfully")
                except Exception:
                    logger.warning("Session recovery failed, creating new connection...")
                    session.close()
                    # Force new connection from pool
                    session.connection()

            return operation()

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # Check if it's a connection-related error
            is_connection_error = any(term in error_str for term in [
                "connection", "closed", "operational", "timeout",
                "server", "network", "reset", "broken pipe"
            ])

            if is_connection_error and attempt < max_retries:
                logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}")
                continue
            else:
                raise

    raise last_error


def query_in_batches(
    session: Session,
    query,
    batch_size: int = 100,
    id_column = None
):
    """
    Execute a query in batches to avoid long-running transactions.

    Args:
        session: SQLAlchemy session
        query: Base query to execute
        batch_size: Number of records per batch
        id_column: Column to use for ordering/pagination (defaults to 'id')

    Yields:
        Records from the query in batches
    """
    offset = 0
    while True:
        batch = query.limit(batch_size).offset(offset).all()
        if not batch:
            break

        for record in batch:
            yield record

        if len(batch) < batch_size:
            break

        offset += batch_size

        # Small commit to release locks
        try:
            session.commit()
        except Exception:
            pass
