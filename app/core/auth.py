import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from argon2 import PasswordHasher

from app.schemas.token import TokenData
from app.schemas.user import UserResponse
from app.storage import storage


class SecurityService:
    """
    Handles all security-related operations including password hashing,
    JWT token generation, and user authentication.
    """

    def __init__(self) -> None:
        self.secret_key = os.getenv(
            "SECRET_KEY", "your-secret-key-change-me-in-production"
        )
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.pwd_hasher = PasswordHasher()
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hashed version."""
        try:
            return self.pwd_hasher.verify(hashed_password, plain_password)
        except Exception:
            return False

    def get_password_hash(self, password: str) -> str:
        """Generate an Argon2 hash of the password."""
        return self.pwd_hasher.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generate a new JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def get_current_user(self, token: str = Depends(OAuth2PasswordBearer(tokenUrl="auth/login"))) -> UserResponse:
        """
        Dependency to retrieve the currently authenticated user.
        Used as a FastAPI dependency.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
            token_data = TokenData(user_id=user_id)
        except JWTError:
            raise credentials_exception

        user = storage.users.get_by_id(token_data.user_id)
        if user is None:
            raise credentials_exception
        return UserResponse(**user)


# Singleton instance for global use
security_service = SecurityService()
