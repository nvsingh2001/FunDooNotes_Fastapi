from pathlib import Path
from .base import BaseRepository


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
        return None
