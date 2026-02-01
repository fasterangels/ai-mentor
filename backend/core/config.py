import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _default_database_url() -> str:
    """Default DB path. When packaged (AI_MENTOR_PACKAGED=1), use %LOCALAPPDATA%\\AI_Mentor\\data."""
    if os.environ.get("AI_MENTOR_PACKAGED"):
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if not local_app_data:
            local_app_data = str(Path.home())
        data_dir = Path(local_app_data) / "AI_Mentor" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = (data_dir / "ai_mentor.sqlite").resolve()
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"
    return "sqlite+aiosqlite:///./app.db"


@dataclass
class Settings:
    """Application settings loaded from environment variables with safe defaults."""

    app_name: str = "AI Mentoras"
    env: str = "dev"
    database_url: str = ""  # set from from_env
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create Settings from environment variables."""
        db_url = os.getenv("DATABASE_URL") or _default_database_url()
        return cls(
            app_name=os.getenv("APP_NAME", cls.app_name),
            env=os.getenv("ENV", cls.env),
            database_url=db_url,
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings.from_env()

