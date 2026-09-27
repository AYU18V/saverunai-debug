import os
import logging
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def user_response(user: dict) -> dict:
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


async def get_user_by_email(database: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await database.users.find_one({"email": email.lower()})


async def create_user(database: AsyncIOMotorDatabase, *, name: str, email: str, password: str) -> None:
    await database.users.insert_one({
        "name": name.strip(),
        "email": email.lower(),
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc),
    })


async def authenticate_user(database: AsyncIOMotorDatabase, *, email: str, password: str) -> dict | None:
    user = await get_user_by_email(database, email)
    if user is None or not verify_password(password, user["password_hash"]):
        return None
    return user


def _jwt_settings() -> tuple[str, str, int]:
    secret = os.getenv("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM")
    expiration_value = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    if not secret or not algorithm or not expiration_value:
        logger.error("JWT configuration is incomplete")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured.",
        )
    try:
        expires_in_minutes = int(expiration_value)
    except ValueError:
        logger.error("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured.",
        )
    if expires_in_minutes <= 0:
        logger.error("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured.",
        )
    return secret, algorithm, expires_in_minutes


def create_access_token(user_id: ObjectId) -> str:
    secret, algorithm, expires_in_minutes = _jwt_settings()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    }
    return jwt.encode(
        payload,
        secret,
        algorithm=algorithm,
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials | None, database: AsyncIOMotorDatabase) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        secret, algorithm, _ = _jwt_settings()
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=[algorithm],
        )
        user_id = ObjectId(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise unauthorized

    user = await database.users.find_one({"_id": user_id})
    if user is None:
        raise unauthorized
    return user
