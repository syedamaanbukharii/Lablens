"""Authentication: JWT tokens + bcrypt password hashing.

PAVE declared RBAC but had zero actual auth. Here every endpoint that touches
user data requires a valid JWT, and passwords are bcrypt-hashed.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lablens.config import get_settings
from lablens.db.models import User, get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        settings = get_settings()
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        return jwt.encode(
            {"sub": user_id, "email": email, "exp": expire},
            settings.secret_key,
            algorithm=ALGORITHM,
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        settings = get_settings()
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user and pwd_context.verify(password, user.hashed_password):
            return user
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = AuthService.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token.")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token.") from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive.")
    return user
