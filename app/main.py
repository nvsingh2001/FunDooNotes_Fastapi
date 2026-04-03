import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import LoggingMixin, get_logger
from app.storage import init_storage


logger = get_logger()


TAGS_METADATA = [
    {
        "name": "Notes",
        "description": (
            "Create, read, update, and delete notes. "
            "Each note has a title, content, timestamps, and an optional "
            "collection of labels attached via the association endpoints."
        ),
    },
    {
        "name": "Labels",
        "description": (
            "Manage labels that can be attached to notes (many-to-many). "
            "Label names are unique (case-insensitive). "
            "Deleting a label automatically detaches it from all notes."
        ),
    },
    {
        "name": "Auth",
        "description": "User registration and authentication (JWT).",
    },
    {
        "name": "Health",
        "description": "Service liveness check.",
    },
]


class RequestLoggingMiddleware(BaseHTTPMiddleware, LoggingMixin):
    """Logs every request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        self.logger.info(f"→ {request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            self.logger.error(
                f"✗ {request.method} {request.url.path} "
                f"raised {type(exc).__name__} after {elapsed:.1f}ms"
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        level = "warning" if response.status_code >= 400 else "info"
        getattr(self.logger, level)(
            f"← {response.status_code} {request.method} "
            f"{request.url.path} [{elapsed:.1f}ms]"
        )
        return response


class AppFactory(LoggingMixin):
    """Builds and configures the FastAPI application."""

    def __init__(self, title: str, description: str, version: str) -> None:
        self._title = title
        self._description = description
        self._version = version
        self._app: FastAPI | None = None

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        self.logger.info(f"Starting {self._title} v{self._version}")
        try:
            init_storage()
            self.logger.info("Storage initialised successfully")
        except Exception as exc:
            self.logger.error(f"Storage init failed: {exc}")
            raise
        yield
        self.logger.info(f"Shutting down {self._title}")

    def _build_app(self) -> "AppFactory":
        self._app = FastAPI(
            title=self._title,
            description=self._description,
            version=self._version,
            lifespan=self._lifespan,
            openapi_tags=TAGS_METADATA,
            docs_url="/docs",
            redoc_url="/redoc",
            swagger_ui_parameters={
                "defaultModelsExpandDepth": 1,  # show schemas collapsed by default
                "displayRequestDuration": True,  # show request time in Swagger UI
                "filter": True,  # enable endpoint search bar
            },
        )
        return self

    def _register_middleware(self) -> "AppFactory":
        self._app.add_middleware(RequestLoggingMiddleware)  # type: ignore
        return self

    def _register_exception_handlers(self) -> "AppFactory":

        @self._app.exception_handler(Exception)  # type: ignore
        async def _global_handler(request: Request, exc: Exception):
            logger.opt(exception=True).error(
                f"Unhandled {type(exc).__name__} on "
                f"{request.method} {request.url.path}: {exc}"
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )

        return self

    def _register_routers(self) -> "AppFactory":
        from app.routers import notes, labels, auth  # type: ignore

        self._app.include_router(auth.router, prefix="/auth", tags=["Auth"])  # type: ignore
        self._app.include_router(notes.router, prefix="/notes", tags=["Notes"])  # type: ignore
        self._app.include_router(labels.router, prefix="/labels", tags=["Labels"])  # type: ignore

        @self._app.get(  # type: ignore
            "/health",
            tags=["Health"],
            summary="Health check",
            description='Returns `{"status": "ok"}` when the service is running.',
            responses={
                200: {"content": {"application/json": {"example": {"status": "ok"}}}}
            },
        )
        def health_check():
            return {"status": "ok"}

        self.logger.info("All routers registered")
        return self

    def build(self) -> FastAPI:
        (
            self._build_app()
            ._register_middleware()
            ._register_exception_handlers()
            ._register_routers()
        )
        self.logger.info(f"{self._title} build complete")
        return self._app  # type: ignore


def create_app() -> FastAPI:
    return AppFactory(
        title="FundooNotes API",
        description=(
            "A RESTful notes + labels backend built with **FastAPI** "
            "and CSV file persistence.\n\n"
            "## Features\n"
            "- JWT-based **Authentication** and **Authorization**\n"
            "- Full CRUD for **Notes** and **Labels** (User-specific)\n"
            "- Many-to-many note–label associations\n"
            "- Structured logging via Loguru\n"
            "- Pydantic v2 request validation\n\n"
            "## Getting Started\n"
            "1. **Register** a new user via `/auth/register`.\n"
            "2. **Login** via `/auth/login` to receive an access token.\n"
            "3. Use the **Authorize** button (lock icon) to attach the token to all subsequent requests."
        ),
        version="1.0.0",
    ).build()


app = create_app()
