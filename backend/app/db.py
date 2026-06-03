"""Async SQLAlchemy engine and session management.

The engine is created lazily on first use so importing the application (for
unit tests or CLI tooling) never opens a network connection. Production code
acquires a session through the :func:`get_session` FastAPI dependency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings.database_url
        if url.startswith("sqlite"):
            # File-backed SQLite: generous busy timeout to ride out brief write
            # locks under concurrent demo traffic.
            _engine = create_async_engine(url, connect_args={"timeout": 30})
        else:
            _engine = create_async_engine(url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional session, rolling back on error."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
