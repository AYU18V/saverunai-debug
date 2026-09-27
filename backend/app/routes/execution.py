import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.routes.projects import get_authenticated_user_id
from app.schemas.execution import ExecutionRequest, ExecutionResponse
from app.services.project_service import get_project, get_project_file
from app.services.workspace_service import WorkspaceUnavailable, run_workspace_file
router=APIRouter(prefix="/api/execution", tags=["execution"])
logger = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "java": ".java",
    "cpp": ".cpp",
}

@router.post("/run", response_model=ExecutionResponse)
async def run(payload: ExecutionRequest, user_id: str=Depends(get_authenticated_user_id), database: AsyncIOMotorDatabase=Depends(get_database)):
    logger.info("Execution requested: project_id=%s file_path=%s language=%s code_bytes=%d", payload.project_id, payload.file_path, payload.language, len(payload.code.encode("utf-8")))
    file=await get_project_file(database, project_id=payload.project_id, user_id=user_id, path=payload.file_path)
    if file is None: raise HTTPException(status_code=404, detail="Project or file not found")
    if payload.language != file["language"] or not payload.file_path.endswith(LANGUAGE_EXTENSIONS[payload.language]):
        raise HTTPException(status_code=422, detail="Language does not match the selected file")
    try:
        project = await get_project(database, project_id=payload.project_id, user_id=user_id)
        return await run_in_threadpool(run_workspace_file, payload.project_id, user_id, (project or {}).get("files", []), payload.file_path, payload.language, payload.code)
    except WorkspaceUnavailable: return ExecutionResponse(status="unavailable", stderr="Code execution service is unavailable.")
