"""
Database setup and session management using SQLAlchemy.
Supports SQLite by default, compatible with PostgreSQL and MySQL.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import DATABASE_URL

# SQLite specific connect args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

from sqlalchemy import event
from sqlalchemy.engine import Engine

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_compatibility():
    """Defensively ensures user_id exists on existing tables in SQLite."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            for table in ["workspaces", "sources", "datasets", "session_histories"]:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id TEXT;"))
                    conn.commit()
                except Exception:
                    pass
    except Exception:
        pass


ensure_schema_compatibility()



def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Closes the session automatically upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
