import csv
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from app.logger import logger


class BaseRepository(ABC):
    """
    Encapsulates all CSV file I/O for a single entity.

    Subclasses declare:
        file_path : Path   — where the CSV lives
        fields    : list   — ordered column names (must match header row)

    All mutating operations follow the same pattern:
        read-all → mutate-in-memory → write-all (under FileLock)
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
        """Load all rows from the CSV into a list of dicts."""
        if not self.file_path.exists():
            return []
        with open(self.file_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write(self, rows: list[dict]) -> None:
        """Overwrite the CSV with the given rows under a file lock."""
        with FileLock(self._lock_path()):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(rows)

    def _init_file(self) -> None:
        """Write headers if the CSV does not exist yet."""
        if not self.file_path.exists():
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.fields).writeheader()
            logger.info(f"Initialised: {self.file_path}")

    def get_all(self) -> list[dict]:
        rows = self._read()
        logger.info(f"{self.__class__.__name__}.get_all → {len(rows)} rows")
        return rows

    def get_by_id(self, entity_id: str) -> dict | None:
        row = next((r for r in self._read() if r["id"] == entity_id), None)
        if row:
            logger.info(f"{self.__class__.__name__}.get_by_id({entity_id}) → found")
        else:
            logger.warning(
                f"{self.__class__.__name__}.get_by_id({entity_id}) → not found"
            )
        return row

    def delete(self, entity_id: str) -> bool:
        rows = self._read()
        new_rows = [r for r in rows if r["id"] != entity_id]
        if len(new_rows) == len(rows):
            logger.warning(f"{self.__class__.__name__}.delete({entity_id}) → not found")
            return False
        self._write(new_rows)
        self._on_delete(entity_id)  # cascade hook
        logger.info(f"{self.__class__.__name__}.delete({entity_id}) → ok")
        return True

    def _on_delete(self, entity_id: str) -> None:
        """Called after a row is deleted. Override for cascade behaviour."""
        pass

    @abstractmethod
    def create(self, **kwargs) -> dict:
        """Create and persist a new entity. Return the saved dict."""
        ...

    @abstractmethod
    def update(self, entity_id: str, **kwargs) -> dict | None:
        """Update an entity by id. Return updated dict or None if missing."""
        ...


class NoteRepository(BaseRepository):
    """Persistence for Note entities."""

    file_path = Path("data/notes.csv")
    fields = ["id", "title", "content", "created_at", "updated_at"]

    def __init__(
        self,
        note_label_repo: "NoteLabelRepository",
        label_repo: "LabelRepository",
    ) -> None:
        # Dependencies injected so the repo can hydrate labels and cascade
        # deletes without importing globals or coupling to other modules.
        self._note_labels = note_label_repo
        self._labels = label_repo

    def create(self, *, title: str, content: str) -> dict:  # type: ignore
        note = {
            "id": self._new_id(),
            "title": title,
            "content": content,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        rows = self._read()
        rows.append(note)
        self._write(rows)
        logger.info(f"NoteRepository.create → id={note['id']}")
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
                logger.info(f"NoteRepository.update({entity_id}) → ok")
                return self._hydrate(row)
        logger.warning(f"NoteRepository.update({entity_id}) → not found")
        return None

    def get_all(self) -> list[dict]:
        return [self._hydrate(r) for r in self._read()]

    def get_by_id(self, entity_id: str) -> dict | None:
        row = next((r for r in self._read() if r["id"] == entity_id), None)
        if not row:
            logger.warning(f"NoteRepository.get_by_id({entity_id}) → not found")
            return None
        return self._hydrate(row)

    def _hydrate(self, note: dict) -> dict:
        """Attach associated labels to a note dict before returning."""
        note["labels"] = self._note_labels.get_labels_for_note(note["id"], self._labels)
        return note

    def _on_delete(self, entity_id: str) -> None:
        """Cascade: remove all note–label links when a note is deleted."""
        self._note_labels.remove_all_for_note(entity_id)
        logger.info(f"Cascaded note_labels delete for note={entity_id}")


class LabelRepository(BaseRepository):
    """Persistence for Label entities."""

    file_path = Path("data/labels.csv")
    fields = ["id", "name"]

    def __init__(self, note_label_repo: "NoteLabelRepository") -> None:
        self._note_labels = note_label_repo

    def create(self, *, name: str) -> dict:  # type: ignore
        label = {"id": self._new_id(), "name": name}
        rows = self._read()
        rows.append(label)
        self._write(rows)
        logger.info(f"LabelRepository.create → id={label['id']} name={name}")
        return label

    def update(self, entity_id: str, *, name: str) -> dict | None:  # type: ignore
        rows = self._read()
        for row in rows:
            if row["id"] == entity_id:
                row["name"] = name
                self._write(rows)
                logger.info(f"LabelRepository.update({entity_id}) → ok")
                return row
        logger.warning(f"LabelRepository.update({entity_id}) → not found")
        return None

    def _on_delete(self, entity_id: str) -> None:
        """Cascade: remove all note–label links when a label is deleted."""
        self._note_labels.remove_all_for_label(entity_id)
        logger.info(f"Cascaded note_labels delete for label={entity_id}")


class NoteLabelRepository:
    """
    Manages the many-to-many join table between notes and labels.

    Does NOT inherit BaseRepository — the join table has no 'id' column
    and its operations (add / remove / get_for_note) don't map onto the
    standard create / update / delete interface.
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
            logger.info(f"Initialised: {self.file_path}")

    def add(self, note_id: str, label_id: str) -> bool:
        """Attach a label to a note. Returns False if already linked."""
        rows = self._read()
        if any(r["note_id"] == note_id and r["label_id"] == label_id for r in rows):
            logger.warning(f"Association exists: note={note_id} label={label_id}")
            return False
        rows.append({"note_id": note_id, "label_id": label_id})
        self._write(rows)
        logger.info(f"Linked label={label_id} to note={note_id}")
        return True

    def remove(self, note_id: str, label_id: str) -> bool:
        """Detach a label from a note. Returns False if link didn't exist."""
        rows = self._read()
        new_rows = [
            r
            for r in rows
            if not (r["note_id"] == note_id and r["label_id"] == label_id)
        ]
        if len(new_rows) == len(rows):
            logger.warning(f"Association not found: note={note_id} label={label_id}")
            return False
        self._write(new_rows)
        logger.info(f"Unlinked label={label_id} from note={note_id}")
        return True

    def remove_all_for_note(self, note_id: str) -> None:
        self._write([r for r in self._read() if r["note_id"] != note_id])

    def remove_all_for_label(self, label_id: str) -> None:
        self._write([r for r in self._read() if r["label_id"] != label_id])

    def get_labels_for_note(
        self, note_id: str, label_repo: "LabelRepository"
    ) -> list[dict]:
        """Return full label dicts for every label attached to a note."""
        linked_ids = {r["label_id"] for r in self._read() if r["note_id"] == note_id}
        return [r for r in label_repo._read() if r["id"] in linked_ids]


class StorageManager:
    """
    Composes NoteRepository, LabelRepository, and NoteLabelRepository.

    Routers call methods on `storage.notes`, `storage.labels`, and
    `storage.note_labels` — they never import or instantiate repos
    directly. This keeps the application layer completely decoupled from
    the CSV implementation detail.

    Dependency construction order (bottom-up):
        1. NoteLabelRepository   — no dependencies
        2. LabelRepository       — needs NoteLabelRepository (cascade)
        3. NoteRepository        — needs both (cascade + hydration)
    """

    def __init__(self) -> None:
        self.note_labels = NoteLabelRepository()
        self.labels = LabelRepository(note_label_repo=self.note_labels)
        self.notes = NoteRepository(
            note_label_repo=self.note_labels,
            label_repo=self.labels,
        )

    def init_files(self) -> None:
        """Ensure data/ directory and all CSV headers exist."""
        Path("data").mkdir(exist_ok=True)
        self.note_labels._init_file()
        self.labels._init_file()
        self.notes._init_file()


storage = StorageManager()


def init_storage() -> None:
    """Called once at app startup (via FastAPI lifespan hook in main.py)."""
    storage.init_files()
