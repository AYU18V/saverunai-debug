import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.database import get_database
from app.routes.auth import bearer_scheme, database_unavailable
from app.schemas.project import (
    CreateProjectFileRequest,
    CreateProjectRequest,
    ProjectFileResponse,
    ProjectResponse,
    RenameProjectFileRequest,
    UpdateProjectFileRequest,
    UpdateProjectRequest,
    normalize_file_path,
)
from app.services.auth_service import get_current_user
from app.services.project_service import (
    FileAlreadyExistsError,
    create_project,
    create_project_file,
    delete_project_file,
    delete_project,
    get_project,
    get_project_file,
    get_project_files,
    get_projects,
    project_response,
    rename_project_file,
    update_project_file,
    update_project,
)


router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = logging.getLogger(__name__)


async def get_authenticated_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> str:
    try:
        user = await get_current_user(credentials, database)
    except PyMongoError:
        logger.exception("MongoDB failed while validating a project request")
        raise database_unavailable()
    return str(user["_id"])


def project_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def file_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


def normalized_file_path(file_path: str) -> str:
    try:
        return normalize_file_path(file_path)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_user_project(
    payload: CreateProjectRequest,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        project = await create_project(database, user_id=user_id, name=payload.name, description=payload.description)
    except PyMongoError:
        logger.exception("MongoDB failed while creating a project")
        raise database_unavailable()
    return project_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_user_projects(
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        projects = await get_projects(database, user_id=user_id)
    except PyMongoError:
        logger.exception("MongoDB failed while listing projects")
        raise database_unavailable()
    return [project_response(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def read_user_project(
    project_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        project = await get_project(database, project_id=project_id, user_id=user_id)
    except PyMongoError:
        logger.exception("MongoDB failed while reading a project")
        raise database_unavailable()
    if project is None:
        raise project_not_found()
    return project_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_user_project(
    project_id: str,
    payload: UpdateProjectRequest,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        project = await update_project(
            database,
            project_id=project_id,
            user_id=user_id,
            updates=payload.model_dump(exclude_none=True),
        )
    except PyMongoError:
        logger.exception("MongoDB failed while updating a project")
        raise database_unavailable()
    if project is None:
        raise project_not_found()
    return project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_project(
    project_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        deleted = await delete_project(database, project_id=project_id, user_id=user_id)
    except PyMongoError:
        logger.exception("MongoDB failed while deleting a project")
        raise database_unavailable()
    if not deleted:
        raise project_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/files", response_model=list[ProjectFileResponse])
async def list_project_files(
    project_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        files = await get_project_files(database, project_id=project_id, user_id=user_id)
    except PyMongoError:
        logger.exception("MongoDB failed while listing project files")
        raise database_unavailable()
    if files is None:
        raise project_not_found()
    return files


@router.post("/{project_id}/files", response_model=ProjectFileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(
    project_id: str,
    payload: CreateProjectFileRequest,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        file = await create_project_file(
            database, project_id=project_id, user_id=user_id, path=payload.path,
            content=payload.content, language=payload.language,
        )
    except FileAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A file with this path already exists")
    except PyMongoError:
        logger.exception("MongoDB failed while creating a project file")
        raise database_unavailable()
    if file is None:
        raise project_not_found()
    return file


@router.get("/{project_id}/files/{file_path:path}", response_model=ProjectFileResponse)
async def read_file(
    project_id: str,
    file_path: str,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    path = normalized_file_path(file_path)
    try:
        file = await get_project_file(database, project_id=project_id, user_id=user_id, path=path)
    except PyMongoError:
        logger.exception("MongoDB failed while reading a project file")
        raise database_unavailable()
    if file is None:
        raise file_not_found()
    return file


@router.put("/{project_id}/files/{file_path:path}", response_model=ProjectFileResponse)
async def update_file(
    project_id: str,
    file_path: str,
    payload: UpdateProjectFileRequest,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    path = normalized_file_path(file_path)
    try:
        file = await update_project_file(
            database, project_id=project_id, user_id=user_id, path=path,
            content=payload.content, language=payload.language,
        )
    except PyMongoError:
        logger.exception("MongoDB failed while updating a project file")
        raise database_unavailable()
    if file is None:
        raise file_not_found()
    return file


@router.patch("/{project_id}/files/{file_path:path}", response_model=ProjectFileResponse)
async def rename_file(
    project_id: str,
    file_path: str,
    payload: RenameProjectFileRequest,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    path = normalized_file_path(file_path)
    try:
        file = await rename_project_file(
            database, project_id=project_id, user_id=user_id, path=path, new_path=payload.new_path
        )
    except FileAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A file with this path already exists")
    except PyMongoError:
        logger.exception("MongoDB failed while renaming a project file")
        raise database_unavailable()
    if file is None:
        raise file_not_found()
    return file


@router.delete("/{project_id}/files/{file_path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    project_id: str,
    file_path: str,
    user_id: str = Depends(get_authenticated_user_id),
    database: AsyncIOMotorDatabase = Depends(get_database),
):
    path = normalized_file_path(file_path)
    try:
        deleted = await delete_project_file(database, project_id=project_id, user_id=user_id, path=path)
    except PyMongoError:
        logger.exception("MongoDB failed while deleting a project file")
        raise database_unavailable()
    if not deleted:
        raise file_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
