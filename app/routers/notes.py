from fastapi import APIRouter, HTTPException, status

from app.logger import get_logger
from app.schemas import NoteCreate, NoteResponse, NoteUpdate
from app.storage import StorageManager

logger = get_logger()


class NotesRouter:
    """
    Registers all /notes endpoints on an APIRouter.

    Instantiate with a StorageManager and read the `.router`
    attribute to pass into FastAPI's include_router().
    """

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self.router = APIRouter()
        self._register_routes()

    def _get_note_or_404(self, note_id: str) -> dict:
        """Fetch a note by id or raise HTTP 404. Shared by multiple endpoints."""
        note = self._storage.notes.get_by_id(note_id)
        if not note:
            logger.warning(f"Note not found: id={note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with id '{note_id}' not found.",
            )
        return note

    def _register_routes(self) -> None:
        """Bind all endpoint methods to their paths and HTTP methods."""

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
            description="Update a note's title and/or content. Send only the fields you want to change.",
        )
        self.router.add_api_route(
            path="/{note_id}",
            endpoint=self.delete_note,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a note",
            description="Permanently delete a note and remove all its label associations.",
        )
        self.router.add_api_route(
            path="/{note_id}/labels/{label_id}",
            endpoint=self.add_label,
            methods=["POST"],
            response_model=NoteResponse,
            status_code=status.HTTP_200_OK,
            summary="Add a label to a note",
            description="Associate an existing label with a note (many-to-many).",
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

    def create_note(self, payload: NoteCreate) -> dict:
        note = self._storage.notes.create(
            title=payload.title,
            content=payload.content,
        )
        logger.info(f"POST /notes/ → created id={note['id']}")
        return note

    def get_all_notes(self) -> list[dict]:
        notes = self._storage.notes.get_all()
        logger.info(f"GET /notes/ → {len(notes)} notes")
        return notes

    def get_note(self, note_id: str) -> dict:
        return self._get_note_or_404(note_id)

    def update_note(self, note_id: str, payload: NoteUpdate) -> dict:
        self._get_note_or_404(note_id)  # guard: 404 before attempting update
        updated = self._storage.notes.update(
            note_id,
            title=payload.title,
            content=payload.content,
        )
        logger.info(f"PUT /notes/{note_id} → updated")
        return updated  # type: ignore

    def delete_note(self, note_id: str) -> None:
        self._get_note_or_404(note_id)  # guard: 404 before attempting delete
        self._storage.notes.delete(note_id)
        logger.info(f"DELETE /notes/{note_id} → deleted")

    def add_label(self, note_id: str, label_id: str) -> dict:
        self._get_note_or_404(note_id)

        label = self._storage.labels.get_by_id(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label with id '{label_id}' not found.",
            )

        linked = self._storage.note_labels.add(note_id, label_id)
        if not linked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Label '{label_id}' is already attached to this note.",
            )

        logger.info(f"POST /notes/{note_id}/labels/{label_id} → linked")
        return self._get_note_or_404(note_id)

    def remove_label(self, note_id: str, label_id: str) -> dict:
        self._get_note_or_404(note_id)

        removed = self._storage.note_labels.remove(note_id, label_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label '{label_id}' is not attached to this note.",
            )

        logger.info(f"DELETE /notes/{note_id}/labels/{label_id} → unlinked")
        return self._get_note_or_404(note_id)


from app.storage import storage as _storage  # noqa: E402

_notes_router = NotesRouter(storage=_storage)
router = _notes_router.router
