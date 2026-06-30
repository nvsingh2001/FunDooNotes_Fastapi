from .base import BaseRepository
from app.repositories.strategy import StorageStrategy

class LabelRepository(BaseRepository):

    def __init__(self, strategy: StorageStrategy, note_label_repo: "NoteLabelRepository") -> None:
        super().__init__(strategy)
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
