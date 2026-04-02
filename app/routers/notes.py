from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.logger import LoggingMixin
from app.schemas import NoteCreate, NoteResponse, NoteUpdate, UserResponse
from app.storage import StorageManager


class NotesRouter(LoggingMixin):
    """Registers all /notes endpoints on an APIRouter."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self.router = APIRouter()
        self._register_routes()

    def _get_note_or_404(self, note_id: str, current_user: UserResponse) -> dict:
        note = self._storage.notes.get_by_id(note_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with id '{note_id}' not found.",
            )
        if note["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this note.",
            )
        return note

    def _get_label_or_404(self, label_id: str, current_user: UserResponse) -> dict:
        label = self._storage.labels.get_by_id(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label with id '{label_id}' not found.",
            )
        if label["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this label.",
            )
        return label

    def _register_routes(self) -> None:
        self.router.add_api_route(
            path="/",
            endpoint=self.create_note,
            methods=["POST"],
            response_model=NoteResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Create a note",
            description="Create a new note with a title and content.",
        )
        self.router.add_api_route(
            path="/",
            endpoint=self.get_all_notes,
            methods=["GET"],
            response_model=list[NoteResponse],
            status_code=status.HTTP_200_OK,
            summary="Get all notes",
            description="Retrieve every note along with its associated labels.",
        )
        self.router.add_api_route(
            path="/{note_id}",
            endpoint=self.get_note,
            methods=["GET"],
            response_model=NoteResponse,
            status_code=status.HTTP_200_OK,
            summary="Get a note by ID",
            description="Retrieve a single note by its UUID.",
        )
        self.router.add_api_route(
            path="/{note_id}",
            endpoint=self.update_note,
            methods=["PUT"],
            response_model=NoteResponse,
            status_code=status.HTTP_200_OK,
            summary="Update a note",
            description="Update a note's title and/or content.",
        )
        self.router.add_api_route(
            path="/{note_id}",
            endpoint=self.delete_note,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a note",
            description="Delete a note and remove all its label associations.",
        )
        self.router.add_api_route(
            path="/{note_id}/labels/{label_id}",
            endpoint=self.add_label,
            methods=["POST"],
            response_model=NoteResponse,
            status_code=status.HTTP_200_OK,
            summary="Add a label to a note",
            description="Associate an existing label with a note.",
        )
        self.router.add_api_route(
            path="/{note_id}/labels/{label_id}",
            endpoint=self.remove_label,
            methods=["DELETE"],
            response_model=NoteResponse,
            status_code=status.HTTP_200_OK,
            summary="Remove a label from a note",
            description="Detach a label from a note without deleting either.",
        )

    def create_note(
        self, payload: NoteCreate, current_user: UserResponse = Depends(get_current_user)
    ) -> dict:
        note = self._storage.notes.create(
            user_id=current_user.id, title=payload.title, content=payload.content
        )
        self.logger.info(f"POST /notes/ → 201 id={note['id']} user={current_user.id}")
        return note

    def get_all_notes(
        self, current_user: UserResponse = Depends(get_current_user)
    ) -> list[dict]:
        notes = self._storage.notes.get_all_for_user(current_user.id)
        self.logger.info(f"GET /notes/ → 200 count={len(notes)} user={current_user.id}")
        return notes

    def get_note(
        self, note_id: str, current_user: UserResponse = Depends(get_current_user)
    ) -> dict:
        note = self._get_note_or_404(note_id, current_user)
        self.logger.info(f"GET /notes/{note_id} → 200 user={current_user.id}")
        return note

    def update_note(
        self,
        note_id: str,
        payload: NoteUpdate,
        current_user: UserResponse = Depends(get_current_user),
    ) -> dict:
        self._get_note_or_404(note_id, current_user)
        updated = self._storage.notes.update(
            note_id, title=payload.title, content=payload.content
        )
        self.logger.info(f"PUT /notes/{note_id} → 200 user={current_user.id}")
        return updated  # type: ignore

    def delete_note(
        self, note_id: str, current_user: UserResponse = Depends(get_current_user)
    ) -> None:
        self._get_note_or_404(note_id, current_user)
        self._storage.notes.delete(note_id)
        self.logger.info(f"DELETE /notes/{note_id} → 204 user={current_user.id}")

    def add_label(
        self,
        note_id: str,
        label_id: str,
        current_user: UserResponse = Depends(get_current_user),
    ) -> dict:
        self._get_note_or_404(note_id, current_user)
        self._get_label_or_404(label_id, current_user)
        linked = self._storage.note_labels.add(note_id, label_id)
        if not linked:
            self.logger.warning(
                f"POST /notes/{note_id}/labels/{label_id} → 400 already linked"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Label '{label_id}' is already attached to this note.",
            )
        self.logger.info(
            f"POST /notes/{note_id}/labels/{label_id} → 200 user={current_user.id}"
        )
        return self._get_note_or_404(note_id, current_user)

    def remove_label(
        self,
        note_id: str,
        label_id: str,
        current_user: UserResponse = Depends(get_current_user),
    ) -> dict:
        self._get_note_or_404(note_id, current_user)
        # Ensure the label also belongs to the user, even for removal
        self._get_label_or_404(label_id, current_user)

        removed = self._storage.note_labels.remove(note_id, label_id)
        if not removed:
            self.logger.warning(
                f"DELETE /notes/{note_id}/labels/{label_id} → 404 not linked"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label '{label_id}' is not attached to this note.",
            )
        self.logger.info(
            f"DELETE /notes/{note_id}/labels/{label_id} → 200 user={current_user.id}"
        )
        return self._get_note_or_404(note_id, current_user)


from app.storage import storage as _storage  # noqa: E402

_notes_router = NotesRouter(storage=_storage)
router = _notes_router.router
