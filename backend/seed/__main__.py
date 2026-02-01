"""CLI entry: run canonical seed. Usage: python -m seed (from backend dir)."""
from __future__ import annotations

import asyncio
import sys

from core.config import get_settings
from core.database import init_database, get_database_manager
from seed.seed_canonical import seed_canonical


async def _main() -> int:
    settings = get_settings()
    await init_database(settings.database_url)
    manager = get_database_manager()
    async with manager.session() as session:
        counts = await seed_canonical(session)
    print("Seed complete:", counts)
    return 0


def main() -> None:
    exit_code = asyncio.run(_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
