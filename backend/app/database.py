"""
SQLAlchemy engine and session factory.

`SessionLocal` is the session class used by FastAPI's `get_db()` dependency.
`pool_pre_ping=True` issues a lightweight SELECT before each connection checkout
to detect and evict stale connections that went away during Docker restarts.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # avoids stale connection errors after Docker restarts
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
