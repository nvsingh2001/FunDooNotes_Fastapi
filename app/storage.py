from pathlib import Path

from app.core.logger import LoggingMixin
from app.repositories.strategy import CSVStorageStrategy
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
        data_dir = Path("data")
        user_strategy = CSVStorageStrategy(data_dir / "users.csv", ["id", "username", "email", "hashed_password"])
        note_label_strategy = CSVStorageStrategy(data_dir / "note_labels.csv", ["note_id", "label_id"])
        label_strategy = CSVStorageStrategy(data_dir / "labels.csv", ["id", "user_id", "name"])
        note_strategy = CSVStorageStrategy(data_dir / "notes.csv", ["id", "user_id", "title", "content", "created_at", "updated_at"])

        self.users = UserRepository(user_strategy)
        self.note_labels = NoteLabelRepository(note_label_strategy)
        self.labels = LabelRepository(label_strategy, note_label_repo=self.note_labels)
        self.notes = NoteRepository(
            note_strategy,
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
