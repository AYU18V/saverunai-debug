import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials

from app.database import get_database
from app.services.auth_service import get_current_user
from app.services.project_service import get_project
from app.services.workspace_service import WorkspaceUnavailable, open_terminal_socket

router = APIRouter(tags=["terminal"])
logger = logging.getLogger(__name__)
HEARTBEAT_PING = "__webide_ping__"
HEARTBEAT_PONG = "__webide_pong__"


@router.websocket("/api/terminal/{project_id}")
async def terminal(websocket: WebSocket, project_id: str):
    # Browsers cannot set an Authorization header on native WebSocket creation.
    # The short-lived JWT is therefore supplied as a query parameter and is never logged.
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        database = get_database()
        user = await get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), database)
        project = await get_project(database, project_id=project_id, user_id=str(user["_id"]))
        if project is None:
            await websocket.close(code=1008)
            return
        docker_socket = await asyncio.to_thread(open_terminal_socket, project_id, str(user["_id"]), project.get("files", []))
    except WorkspaceUnavailable:
        await websocket.accept()
        await websocket.send_text("\r\nDocker execution service is unavailable.\r\n")
        await websocket.close(code=1011)
        return
    except Exception:
        logger.exception("Terminal authentication or startup failed for project %s", project_id)
        await websocket.close(code=1011)
        return

    await websocket.accept()

    async def read_container():
        while True:
            data = await asyncio.to_thread(docker_socket.recv, 4096)
            if not data:
                break
            await websocket.send_text(data.decode("utf-8", "replace"))

    async def write_container():
        while True:
            message = await websocket.receive_text()
            # Keep browser/proxy idle timeouts from tearing down a healthy
            # terminal without ever sending heartbeat frames to Bash.
            if message == HEARTBEAT_PING:
                await websocket.send_text(HEARTBEAT_PONG)
                continue
            await asyncio.to_thread(docker_socket.sendall, message.encode("utf-8"))

    readers = asyncio.create_task(read_container())
    writers = asyncio.create_task(write_container())
    try:
        done, _ = await asyncio.wait({readers, writers}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            error = task.exception()
            if error and not isinstance(error, WebSocketDisconnect):
                logger.info("Terminal session ended for project %s: %s", project_id, error)
    except WebSocketDisconnect:
        pass
    finally:
        for task in (readers, writers):
            task.cancel()
        await asyncio.gather(readers, writers, return_exceptions=True)
        await asyncio.to_thread(docker_socket.close)
