import logging

from .config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure application-wide logging based on settings.

    The format includes timestamp, log level, logger name, and message.
    """
    log_level_name = settings.log_level.upper()
    level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Align uvicorn loggers with the application log level for consistency.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(level)

