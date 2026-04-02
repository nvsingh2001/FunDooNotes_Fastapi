from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.storage import init_storage

logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs the method, path, and response status
    for every HTTP request passing through the application.

    Inherits from BaseHTTPMiddleware (Starlette) which handles the
    ASGI call/receive/send plumbing — we only override `dispatch`.
    """

    async def dispatch(self, request: Request, call_next):
        logger.info(f"→ {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"← {response.status_code} {request.method} {request.url.path}")
        return response


class AppFactory:
    """
    Builds and configures the FastAPI application.

    Responsibilities:
        - define the lifespan (startup / shutdown hooks)
        - register middleware
        - register exception handlers
        - include routers
        - expose the built `app` instance

    Consumers import `create_app()` and never instantiate this directly.
    """

    def __init__(self, title: str, description: str, version: str) -> None:
        self._title = title
        self._description = description
        self._version = version
        self._app: FastAPI | None = None

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Startup → yield → shutdown."""
        logger.info(f"Starting {self._title} v{self._version}...")
        init_storage()
        yield
        logger.info(f"Shutting down {self._title}.")

    def _build_app(self) -> "AppFactory":
        self._app = FastAPI(
            title=self._title,
            description=self._description,
            version=self._version,
            lifespan=self._lifespan,
        )
        return self

    def _register_middleware(self) -> "AppFactory":
        self._app.add_middleware(RequestLoggingMiddleware)  # type: ignore
        return self

    def _register_exception_handlers(self) -> "AppFactory":

        @self._app.exception_handler(Exception)  # type: ignore
        async def _global_handler(request: Request, exc: Exception):
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}: {exc}"
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )

        return self

    def _register_routers(self) -> "AppFactory":
        from app.routers import notes, labels

        self._app.include_router(notes.router, prefix="/notes", tags=["Notes"])  # type: ignore
        self._app.include_router(labels.router, prefix="/labels", tags=["Labels"])  # type: ignore

        @self._app.get("/health", tags=["Health"])  # type: ignore
        def health_check():
            """Returns 200 if the service is up."""
            return {"status": "ok"}

        return self

    def build(self) -> FastAPI:
        """Run the full build pipeline and return the FastAPI instance."""
        (
            self._build_app()
            ._register_middleware()
            ._register_exception_handlers()
            ._register_routers()
        )
        return self._app  # type: ignore


def create_app() -> FastAPI:
    return AppFactory(
        title="FundooNotes API",
        description="A notes + labels REST API backed by CSV files.",
        version="1.0.0",
    ).build()


# Uvicorn entry point:  uvicorn app.main:app --reload
app = create_app()
