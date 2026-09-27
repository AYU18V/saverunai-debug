from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.routes.projects import get_authenticated_user_id
from app.services.project_service import get_project
from app.services.workspace_service import WorkspaceImageNotBuilt, WorkspaceUnavailable, restart_workspace, start_workspace, stop_workspace, workspace_status

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


async def _project(database, project_id, user_id):
    project = await get_project(database, project_id=project_id, user_id=user_id)
    if project is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _unavailable():
    return {"status": "unavailable", "message": "Docker execution service is unavailable."}


@router.post("/{project_id}/start")
async def start(project_id: str, user_id: str = Depends(get_authenticated_user_id), database: AsyncIOMotorDatabase = Depends(get_database)):
    project = await _project(database, project_id, user_id)
    try: return {"status": start_workspace(project_id, user_id, project.get("files", []))}
    except WorkspaceImageNotBuilt as error: return {"status": "unavailable", "message": str(error)}
    except WorkspaceUnavailable: return _unavailable()


@router.post("/{project_id}/stop")
async def stop(project_id: str, user_id: str = Depends(get_authenticated_user_id), database: AsyncIOMotorDatabase = Depends(get_database)):
    await _project(database, project_id, user_id)
    try: return {"status": stop_workspace(project_id, user_id)}
    except WorkspaceImageNotBuilt as error: return {"status": "unavailable", "message": str(error)}
    except WorkspaceUnavailable: return _unavailable()


@router.post("/{project_id}/restart")
async def restart(project_id: str, user_id: str = Depends(get_authenticated_user_id), database: AsyncIOMotorDatabase = Depends(get_database)):
    project = await _project(database, project_id, user_id)
    try: return {"status": restart_workspace(project_id, user_id, project.get("files", []))}
    except WorkspaceImageNotBuilt as error: return {"status": "unavailable", "message": str(error)}
    except WorkspaceUnavailable: return _unavailable()


@router.get("/{project_id}/status")
async def status(project_id: str, user_id: str = Depends(get_authenticated_user_id), database: AsyncIOMotorDatabase = Depends(get_database)):
    await _project(database, project_id, user_id)
    try: return {"status": workspace_status(project_id, user_id)}
    except WorkspaceUnavailable: return _unavailable()
