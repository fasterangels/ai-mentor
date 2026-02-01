from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD helpers.

    No commits are performed here - commit responsibility is left to the
    service layer.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with an async session."""
        self.session = session

    async def add(self, entity: T) -> T:
        """Add an entity to the session (not committed)."""
        self.session.add(entity)
        return entity

    async def get_by_id(
        self, model: Type[T], id_value: str | int
    ) -> Optional[T]:
        """Get an entity by its primary key."""
        result = await self.session.get(model, id_value)
        return result

    async def list(
        self, model: Type[T], limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities with pagination."""
        stmt = select(model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, entity: T) -> None:
        """Delete an entity from the session (not committed)."""
        await self.session.delete(entity)
