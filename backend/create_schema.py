import asyncio
import sys

from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
import models  # noqa: F401
from tools.schema_check import check_sqlite_schema_mismatch


def _is_sqlite_file_url(url: str) -> bool:
    if not url or "sqlite" not in url.lower():
        return False
    if ":memory:" in url:
        return False
    return True


async def main() -> int:
    settings = get_settings()
    await init_database(settings.database_url)

    engine = get_database_manager().engine
    url = settings.database_url or ""

    if _is_sqlite_file_url(url):
        sync_engine = engine.sync_engine
        has_mismatch, message = check_sqlite_schema_mismatch(sync_engine)
        if has_mismatch:
            print(f"Schema mismatch: {message}", file=sys.stderr)
            await dispose_database()
            return 1

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await dispose_database()
    print("schema ok")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))