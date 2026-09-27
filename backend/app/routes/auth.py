import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.database import get_database
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
    get_user_by_email,
    user_response,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def database_unavailable() -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service is temporarily unavailable.")


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, database: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        if await get_user_by_email(database, payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
        await create_user(database, name=payload.name, email=payload.email, password=payload.password)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    except PyMongoError:
        logger.exception("MongoDB failed while registering a user")
        raise database_unavailable()
    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest, database: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        user = await authenticate_user(database, email=payload.email, password=payload.password)
    except PyMongoError:
        logger.exception("MongoDB failed while authenticating a user")
        raise database_unavailable()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user["_id"]),
        "token_type": "bearer",
        "user": user_response(user),
    }


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        user = await get_current_user(credentials, database)
    except PyMongoError:
        logger.exception("MongoDB failed while loading the current user")
        raise database_unavailable()
    return user_response(user)
