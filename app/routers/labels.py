from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import security_service
from app.core.logger import LoggingMixin
from app.schemas.label import LabelCreate, LabelResponse, LabelUpdate
from app.schemas.user import UserResponse
from app.storage import StorageManager


class LabelsRouter(LoggingMixin):
    """Registers all /labels endpoints on an APIRouter."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self.router = APIRouter()
        self._register_routes()

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

    def _check_name_conflict(
        self, name: str, user_id: str, exclude_id: str | None = None
    ) -> None:
        """Raise 409 if a label with this name (case-insensitive) already exists for the user."""
        conflict = next(
            (
                lb
                for lb in self._storage.labels.get_all_for_user(user_id)
                if lb["name"].lower() == name.lower() and lb["id"] != exclude_id
            ),
            None,
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A label named '{name}' already exists.",
            )

    def _register_routes(self) -> None:
        self.router.add_api_route(
            path="/",
            endpoint=self.create_label,
            methods=["POST"],
            response_model=LabelResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Create a label",
            description="Create a new label that can be attached to notes.",
        )
        self.router.add_api_route(
            path="/",
            endpoint=self.get_all_labels,
            methods=["GET"],
            response_model=list[LabelResponse],
            status_code=status.HTTP_200_OK,
            summary="Get all labels",
            description="Retrieve every label in the system.",
        )
        self.router.add_api_route(
            path="/{label_id}",
            endpoint=self.get_label,
            methods=["GET"],
            response_model=LabelResponse,
            status_code=status.HTTP_200_OK,
            summary="Get a label by ID",
            description="Retrieve a single label by its UUID.",
        )
        self.router.add_api_route(
            path="/{label_id}",
            endpoint=self.update_label,
            methods=["PUT"],
            response_model=LabelResponse,
            status_code=status.HTTP_200_OK,
            summary="Update a label",
            description="Rename an existing label.",
        )
        self.router.add_api_route(
            path="/{label_id}",
            endpoint=self.delete_label,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a label",
            description="Delete a label and detach it from all notes.",
        )

    def create_label(
        self,
        payload: LabelCreate,
        current_user: UserResponse = Depends(security_service.get_current_user),
    ) -> dict:
        self._check_name_conflict(payload.name, user_id=current_user.id)
        label = self._storage.labels.create(user_id=current_user.id, name=payload.name)
        self.logger.info(f"POST /labels/ → 201 id={label['id']} user={current_user.id}")
        return label

    def get_all_labels(
        self, current_user: UserResponse = Depends(security_service.get_current_user)
    ) -> list[dict]:
        labels = self._storage.labels.get_all_for_user(current_user.id)
        self.logger.info(f"GET /labels/ → 200 count={len(labels)} user={current_user.id}")
        return labels

    def get_label(
        self,
        label_id: str,
        current_user: UserResponse = Depends(security_service.get_current_user),
    ) -> dict:
        label = self._get_label_or_404(label_id, current_user)
        self.logger.info(f"GET /labels/{label_id} → 200 user={current_user.id}")
        return label

    def update_label(
        self,
        label_id: str,
        payload: LabelUpdate,
        current_user: UserResponse = Depends(security_service.get_current_user),
    ) -> dict:
        self._get_label_or_404(label_id, current_user)
        self._check_name_conflict(
            payload.name, user_id=current_user.id, exclude_id=label_id
        )
        updated = self._storage.labels.update(label_id, name=payload.name)
        self.logger.info(f"PUT /labels/{label_id} → 200 user={current_user.id}")
        return updated  # type: ignore

    def delete_label(
        self,
        label_id: str,
        current_user: UserResponse = Depends(security_service.get_current_user),
    ) -> None:
        self._get_label_or_404(label_id, current_user)
        self._storage.labels.delete(label_id)
        self.logger.info(f"DELETE /labels/{label_id} → 204 user={current_user.id}")


from app.storage import storage as _storage  # noqa: E402

_labels_router = LabelsRouter(storage=_storage)
router = _labels_router.router
