import csv
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from app.logger import LoggingMixin


class BaseRepository(ABC, LoggingMixin):
    """
    Encapsulates all CSV file I/O for a single entity.
    Inherits LoggingMixin so every subclass gets self.logger for free.
    """

    file_path: Path
    fields: list[str]

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    def _lock_path(self) -> str:
        return str(self.file_path) + ".lock"

    def _read(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write(self, rows: list[dict]) -> None:
        with FileLock(self._lock_path()):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(rows)

    def _init_file(self) -> None:
        # For this version, we reset data if the headers don't match or file doesn't exist
        needs_init = not self.file_path.exists()
        if not needs_init:
            with open(self.file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header != self.fields:
                    needs_init = True

        if needs_init:
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.fields).writeheader()
            self.logger.info(f"Initialised (reset): {self.file_path}")

    def get_all(self) -> list[dict]:
        rows = self._read()
        self.logger.info(f"get_all → {len(rows)} rows")
        return rows

    def get_by_id(self, entity_id: str) -> dict | None:
        row = next((r for r in self._read() if r["id"] == entity_id), None)
        if row:
            self.logger.info(f"get_by_id({entity_id}) → found")
        else:
            self.logger.warning(f"get_by_id({entity_id}) → not found")
        return row

    def delete(self, entity_id: str) -> bool:
        rows = self._read()
        new_rows = [r for r in rows if r["id"] != entity_id]
        if len(new_rows) == len(rows):
            self.logger.warning(f"delete({entity_id}) → not found")
            return False
        self._write(new_rows)
        self._on_delete(entity_id)
        self.logger.info(f"delete({entity_id}) → ok")
        return True

    def _on_delete(self, entity_id: str) -> None:
        """Override in subclasses for cascade behaviour."""
        pass

    @abstractmethod
    def create(self, **kwargs) -> dict: ...

    @abstractmethod
    def update(self, entity_id: str, **kwargs) -> dict | None: ...


class UserRepository(BaseRepository):
    file_path = Path("data/users.csv")
    fields = ["id", "username", "email", "hashed_password"]

    def create(self, *, username: str, email: str, hashed_password: str) -> dict:  # type: ignore
        user = {
            "id": self._new_id(),
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
        }
        rows = self._read()
        rows.append(user)
        self._write(rows)
        self.logger.info(f"create → id={user['id']} username='{username}'")
        return user

    def get_by_username(self, username: str) -> dict | None:
        return next((r for r in self._read() if r["username"] == username), None)

    def get_by_email(self, email: str) -> dict | None:
        return next((r for r in self._read() if r["email"] == email), None)

    def update(self, entity_id: str, **kwargs) -> dict | None:
        # Not needed for basic auth implementation
        return None


class NoteRepository(BaseRepository):
    file_path = Path("data/notes.csv")
    fields = ["id", "user_id", "title", "content", "created_at", "updated_at"]

    def __init__(
        self,
        note_label_repo: "NoteLabelRepository",
        label_repo: "LabelRepository",
    ) -> None:
        self._note_labels = note_label_repo
        self._labels = label_repo

    def create(self, *, user_id: str, title: str, content: str) -> dict:  # type: ignore
        note = {
            "id": self._new_id(),
            "user_id": user_id,
            "title": title,
            "content": content,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        rows = self._read()
        rows.append(note)
        self._write(rows)
        self.logger.info(f"create → id={note['id']} title='{title}' user_id='{user_id}'")
        return self._hydrate(note)

    def update(  # type: ignore
        self, entity_id: str, *, title: str | None = None, content: str | None = None
    ) -> dict | None:
        rows = self._read()
        for row in rows:
            if row["id"] == entity_id:
                if title is not None:
                    row["title"] = title
                if content is not None:
                    row["content"] = content
                row["updated_at"] = self._now()
                self._write(rows)
                self.logger.info(f"update({entity_id}) → ok")
                return self._hydrate(row)
        self.logger.warning(f"update({entity_id}) → not found")
        return None

    def get_all_for_user(self, user_id: str) -> list[dict]:
        rows = [r for r in self._read() if r["user_id"] == user_id]
        self.logger.info(f"get_all_for_user({user_id}) → {len(rows)} notes")
        return [self._hydrate(r) for r in rows]

    def get_by_id(self, entity_id: str) -> dict | None:
        row = next((r for r in self._read() if r["id"] == entity_id), None)
        if not row:
            self.logger.warning(f"get_by_id({entity_id}) → not found")
            return None
        self.logger.info(f"get_by_id({entity_id}) → found")
        return self._hydrate(row)

    def _hydrate(self, note: dict) -> dict:
        note["labels"] = self._note_labels.get_labels_for_note(note["id"], self._labels)
        return note

    def _on_delete(self, entity_id: str) -> None:
        self._note_labels.remove_all_for_note(entity_id)
        self.logger.info(f"cascade: removed note_labels for note={entity_id}")


class LabelRepository(BaseRepository):
    file_path = Path("data/labels.csv")
    fields = ["id", "user_id", "name"]

    def __init__(self, note_label_repo: "NoteLabelRepository") -> None:
        self._note_labels = note_label_repo

    def create(self, *, user_id: str, name: str) -> dict:  # type: ignore
        label = {"id": self._new_id(), "user_id": user_id, "name": name}
        rows = self._read()
        rows.append(label)
        self._write(rows)
        self.logger.info(f"create → id={label['id']} name='{name}' user_id='{user_id}'")
        return label

    def update(self, entity_id: str, *, name: str) -> dict | None:  # type: ignore
        rows = self._read()
        for row in rows:
            if row["id"] == entity_id:
                row["name"] = name
                self._write(rows)
                self.logger.info(f"update({entity_id}) → name='{name}'")
                return row
        self.logger.warning(f"update({entity_id}) → not found")
        return None

    def get_all_for_user(self, user_id: str) -> list[dict]:
        rows = [r for r in self._read() if r["user_id"] == user_id]
        self.logger.info(f"get_all_for_user({user_id}) → {len(rows)} labels")
        return rows

    def _on_delete(self, entity_id: str) -> None:
        self._note_labels.remove_all_for_label(entity_id)
        self.logger.info(f"cascade: removed note_labels for label={entity_id}")


class NoteLabelRepository(LoggingMixin):
    """
    Many-to-many join table. Does not inherit BaseRepository
    (no id column, different interface). Inherits LoggingMixin directly.
    """

    file_path = Path("data/note_labels.csv")
    fields = ["note_id", "label_id"]

    def _lock_path(self) -> str:
        return str(self.file_path) + ".lock"

    def _read(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write(self, rows: list[dict]) -> None:
        with FileLock(self._lock_path()):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(rows)

    def _init_file(self) -> None:
        if not self.file_path.exists():
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.fields).writeheader()
            self.logger.info(f"Initialised: {self.file_path}")

    def add(self, note_id: str, label_id: str) -> bool:
        rows = self._read()
        if any(r["note_id"] == note_id and r["label_id"] == label_id for r in rows):
            self.logger.warning(f"add → already linked note={note_id} label={label_id}")
            return False
        rows.append({"note_id": note_id, "label_id": label_id})
        self._write(rows)
        self.logger.info(f"add → linked note={note_id} label={label_id}")
        return True

    def remove(self, note_id: str, label_id: str) -> bool:
        rows = self._read()
        new_rows = [
            r
            for r in rows
            if not (r["note_id"] == note_id and r["label_id"] == label_id)
        ]
        if len(new_rows) == len(rows):
            self.logger.warning(f"remove → not found note={note_id} label={label_id}")
            return False
        self._write(new_rows)
        self.logger.info(f"remove → unlinked note={note_id} label={label_id}")
        return True

    def remove_all_for_note(self, note_id: str) -> None:
        self._write([r for r in self._read() if r["note_id"] != note_id])
        self.logger.info(f"remove_all_for_note({note_id}) → done")

    def remove_all_for_label(self, label_id: str) -> None:
        self._write([r for r in self._read() if r["label_id"] != label_id])
        self.logger.info(f"remove_all_for_label({label_id}) → done")

    def get_labels_for_note(
        self, note_id: str, label_repo: "LabelRepository"
    ) -> list[dict]:
        linked_ids = {r["label_id"] for r in self._read() if r["note_id"] == note_id}
        return [r for r in label_repo._read() if r["id"] in linked_ids]


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
