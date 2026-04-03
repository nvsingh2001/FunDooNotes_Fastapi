from pathlib import Path
from .base import BaseRepository

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
