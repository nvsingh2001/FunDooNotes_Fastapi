from pathlib import Path

from app.core.logger import LoggingMixin
from app.repositories.user import UserRepository
from app.repositories.note import NoteRepository
from app.repositories.label import LabelRepository
from app.repositories.note_label import NoteLabelRepository


class StorageManager(LoggingMixin):
    """
    Composes all repositories into a single access point.
    Inherits LoggingMixin for startup/shutdown logging.
    """

    def __init__(self) -> None:
        self.users = UserRepository()
        self.note_labels = NoteLabelRepository()
        self.labels = LabelRepository(note_label_repo=self.note_labels)
        self.notes = NoteRepository(
            note_label_repo=self.note_labels,
            label_repo=self.labels,
        )

    def init_files(self) -> None:
        Path("data").mkdir(exist_ok=True)
        self.users._init_file()
        self.note_labels._init_file()
        self.labels._init_file()
        self.notes._init_file()
        self.logger.info("All storage files ready")


storage = StorageManager()


def init_storage() -> None:
    storage.init_files()
