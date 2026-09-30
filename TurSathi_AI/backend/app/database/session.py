from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Create SQLAlchemy Engine for PostgreSQL with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# Session factory bound to engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency generator yielding a database session per request.
    Ensures proper cleanup and closure after handling requests.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
