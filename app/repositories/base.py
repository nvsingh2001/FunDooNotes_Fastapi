import csv
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from app.core.logger import LoggingMixin


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
