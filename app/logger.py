import sys
from pathlib import Path

from loguru import logger as _loguru_logger


class AppLogger:
    """
    Configures and manages the application-wide Loguru logger.

    Usage:
        from app.logger import get_logger
        logger = get_logger()
        logger.info("something happened")
    """

    _instance: "AppLogger | None" = None  # singleton holder
    _configured: bool = False

    LOG_DIR = Path("logs")
    LOG_FILE = LOG_DIR / "app.log"

    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )
    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}"
    )

    def __new__(cls) -> "AppLogger":
        """Enforce singleton — only one AppLogger ever exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self) -> None:
        """
        Set up console and file sinks.
        Safe to call multiple times — configuration is applied only once.
        """
        if self._configured:
            return

        self.LOG_DIR.mkdir(exist_ok=True)

        _loguru_logger.remove()  # drop Loguru's default sink

        _loguru_logger.add(
            sys.stdout,
            level="INFO",
            format=self.CONSOLE_FORMAT,
            colorize=True,
        )

        _loguru_logger.add(
            str(self.LOG_FILE),
            level="INFO",
            format=self.FILE_FORMAT,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )

        AppLogger._configured = True

    def get_logger(self):
        """Return the configured Loguru logger instance."""
        self.configure()
        return _loguru_logger


def get_logger():
    """
    Returns the singleton configured logger.
    Import and call this anywhere in the app:

        from app.logger import get_logger
        logger = get_logger()
    """
    return AppLogger().get_logger()


logger = get_logger()
