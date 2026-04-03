import csv
from pathlib import Path
from filelock import FileLock
from app.core.logger import LoggingMixin

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
