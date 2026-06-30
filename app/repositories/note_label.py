from app.core.logger import LoggingMixin
from app.repositories.strategy import StorageStrategy

class NoteLabelRepository(LoggingMixin):
    """
    Many-to-many join table. Does not inherit BaseRepository
    (no id column, different interface). Inherits LoggingMixin directly.
    """

    def __init__(self, strategy: StorageStrategy) -> None:
        self._strategy = strategy

    def _read(self) -> list[dict]:
        return self._strategy.read()

    def _write(self, rows: list[dict]) -> None:
        self._strategy.write(rows)

    def _init_file(self) -> None:
        self._strategy.init_file()
        self.logger.info("Storage strategy initialised")

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
