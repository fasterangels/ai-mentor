from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_database_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession from the DatabaseManager."""
    manager = get_database_manager()
    async with manager.session() as session:
        yield session

