from fastapi import APIRouter, HTTPException, status

from app.logger import get_logger
from app.schemas import LabelCreate, LabelResponse, LabelUpdate
from app.storage import StorageManager

logger = get_logger()


class LabelsRouter:
    """
    Registers all /labels endpoints on an APIRouter.

    Instantiate with a StorageManager and read the `.router`
    attribute to pass into FastAPI's include_router().
    """

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self.router = APIRouter()
        self._register_routes()

    def _get_label_or_404(self, label_id: str) -> dict:
        """Fetch a label by id or raise HTTP 404. Shared by multiple endpoints."""
        label = self._storage.labels.get_by_id(label_id)
        if not label:
            logger.warning(f"Label not found: id={label_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label with id '{label_id}' not found.",
            )
        return label

    def _register_routes(self) -> None:
        """Bind all endpoint methods to their paths and HTTP methods."""

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
            description=(
                "Permanently delete a label and remove it from all "
                "notes it was attached to."
            ),
        )

    def create_label(self, payload: LabelCreate) -> dict:
        existing = [
            lb
            for lb in self._storage.labels.get_all()
            if lb["name"].lower() == payload.name.lower()
        ]
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A label named '{payload.name}' already exists.",
            )

        label = self._storage.labels.create(name=payload.name)
        logger.info(f"POST /labels/ → created id={label['id']}")
        return label

    def get_all_labels(self) -> list[dict]:
        labels = self._storage.labels.get_all()
        logger.info(f"GET /labels/ → {len(labels)} labels")
        return labels

    def get_label(self, label_id: str) -> dict:
        return self._get_label_or_404(label_id)

    def update_label(self, label_id: str, payload: LabelUpdate) -> dict:
        self._get_label_or_404(label_id)  # guard: 404 before attempting update

        existing = [
            lb
            for lb in self._storage.labels.get_all()
            if lb["name"].lower() == payload.name.lower() and lb["id"] != label_id
        ]
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A label named '{payload.name}' already exists.",
            )

        updated = self._storage.labels.update(label_id, name=payload.name)
        logger.info(f"PUT /labels/{label_id} → updated")
        return updated  # type: ignore

    def delete_label(self, label_id: str) -> None:
        self._get_label_or_404(label_id)  # guard: 404 before attempting delete
        self._storage.labels.delete(label_id)
        logger.info(f"DELETE /labels/{label_id} → deleted")


from app.storage import storage as _storage  # noqa: E402

_labels_router = LabelsRouter(storage=_storage)
router = _labels_router.router
