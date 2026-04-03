import sys
from pathlib import Path

from loguru import logger as _loguru_logger


class AppLogger:
    """Configures and owns the application-wide Loguru logger."""

    _instance: "AppLogger | None" = None
    _configured: bool = False

    LOG_DIR = Path("logs")
    APP_LOG = LOG_DIR / "app.log"
    ERROR_LOG = LOG_DIR / "error.log"

    CONSOLE_FORMAT = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )
    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:<8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    def __new__(cls) -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self) -> None:
        """
        Register all sinks. Idempotent — safe to call more than once.
        Three sinks:
            1. stdout       — INFO+, coloured
            2. app.log      — INFO+, structured, rotates at 10 MB
            3. error.log    — ERROR only, never rotated, retained 30 days
        """
        if self._configured:
            return

        self.LOG_DIR.mkdir(exist_ok=True)
        _loguru_logger.remove()

        _loguru_logger.add(
            sys.stdout,
            level="INFO",
            format=self.CONSOLE_FORMAT,
            colorize=True,
            backtrace=False,
            diagnose=False,
        )

        _loguru_logger.add(
            str(self.APP_LOG),
            level="INFO",
            format=self.FILE_FORMAT,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
            backtrace=True,
            diagnose=False,  # set True locally to see variable values
        )

        _loguru_logger.add(
            str(self.ERROR_LOG),
            level="ERROR",
            format=self.FILE_FORMAT,
            rotation=None,  # never rotate — errors must persist
            retention="30 days",
            encoding="utf-8",
            backtrace=True,
            diagnose=False,
        )

        AppLogger._configured = True
        _loguru_logger.info(
            f"Logging configured — app={self.APP_LOG}, errors={self.ERROR_LOG}"
        )

    def get_logger(self):
        self.configure()
        return _loguru_logger


class LoggingMixin:
    """
    Mixin that provides a `self.logger` property pre-bound with the
    class name as context.

    Usage:
        class NoteRepository(BaseRepository, LoggingMixin):
            def create(self, ...):
                self.logger.info("Note created")
                # logs as: NoteRepository | Note created

    The mixin is intentionally stateless — it adds no __init__,
    carries no instance data, and imposes no constructor contract on
    the classes that use it. Safe to combine with any base class.
    """

    @property
    def logger(self):
        return _loguru_logger.bind(classname=self.__class__.__name__)


def get_logger():
    """Return the singleton configured logger."""
    return AppLogger().get_logger()


# Pre-configured instance: `from app.logger import logger`
logger = get_logger()
