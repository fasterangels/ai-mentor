import asyncio

from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
import models  # φορτώνει όλα τα canonical models


async def main():
    settings = get_settings()
    await init_database(settings.database_url)

    engine = get_database_manager().engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await dispose_database()
    print("schema ok")


if __name__ == "__main__":
    asyncio.run(main())