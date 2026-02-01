from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async database manager with a single engine and session factory."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

    async def init(self) -> None:
        """Initialize the async engine and sessionmaker if not already initialized."""
        if self._engine is not None:
            return

        logger.info("Initializing async database engine")
        self._engine = create_async_engine(
            self._database_url,
            echo=False,
            future=True,
        )

        # SQLite-specific pragmas for better safety and concurrency.
        if self._database_url.startswith("sqlite+aiosqlite"):

            @event.listens_for(self._engine.sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[override]  # pragma: no cover
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                try:
                    cursor.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    # journal_mode may not be supported in all environments; ignore failures
                    logger.debug("SQLite WAL journal_mode not applied")
                finally:
                    cursor.close()

        self._sessionmaker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        logger.info("Async database engine and sessionmaker initialized")

    async def dispose(self) -> None:
        """Dispose of the engine and clear the sessionmaker."""
        if self._engine is not None:
            logger.info("Disposing async database engine")
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager yielding an AsyncSession.

        Ensures commit on success and rollback on errors.
        """
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseManager is not initialized. Call init() first.")

        session: AsyncSession = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @property
    def engine(self) -> Optional[AsyncEngine]:
        return self._engine


_db_manager: Optional[DatabaseManager] = None


async def init_database(database_url: str) -> None:
    """Create and initialize the global DatabaseManager singleton."""
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    await _db_manager.init()


async def dispose_database() -> None:
    """Dispose the global DatabaseManager singleton."""
    global _db_manager

    if _db_manager is not None:
        await _db_manager.dispose()
        _db_manager = None


def get_database_manager() -> DatabaseManager:
    """Return the initialized DatabaseManager instance."""
    if _db_manager is None:
        raise RuntimeError("DatabaseManager is not initialized.")
    return _db_manager

