from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import security_service
from app.core.logger import LoggingMixin
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.storage import StorageManager


class AuthRouter(LoggingMixin):
    """Registers all /auth endpoints on an APIRouter."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            path="/register",
            endpoint=self.register,
            methods=["POST"],
            response_model=UserResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Register a new user",
        )
        self.router.add_api_route(
            path="/login",
            endpoint=self.login,
            methods=["POST"],
            response_model=Token,
            summary="Login for access token",
        )

    def register(self, payload: UserCreate) -> dict:
        if self._storage.users.get_by_username(payload.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
        if self._storage.users.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = security_service.get_password_hash(payload.password)
        user = self._storage.users.create(
            username=payload.username,
            email=payload.email,
            hashed_password=hashed_password,
        )
        self.logger.info(f"User registered: {payload.username}")
        return user

    def login(self, form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
        user = self._storage.users.get_by_username(form_data.username)
        if not user or not security_service.verify_password(
            form_data.password, user["hashed_password"]
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(
            minutes=security_service.access_token_expire_minutes
        )
        access_token = security_service.create_access_token(
            data={"sub": user["id"]}, expires_delta=access_token_expires
        )
        self.logger.info(f"User logged in: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}


from app.storage import storage as _storage  # noqa: E402

_auth_router = AuthRouter(storage=_storage)
router = _auth_router.router
