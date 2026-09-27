"""Docker-only lifecycle and file synchronization for persistent project workspaces."""
import io
import logging
import os
import time
from hashlib import sha256

import docker
from docker.errors import DockerException, ImageNotFound, NotFound

logger = logging.getLogger(__name__)
WORKSPACE_IMAGE = os.getenv("WORKSPACE_IMAGE", "webide-dev:1.0")

# These are explicit executable paths/commands for execs *inside* a workspace.
# Do not rely on the image ENTRYPOINT: Docker does not apply it to exec_run.
LANGUAGE_COMMANDS = {
    "python": ["/usr/bin/python3.11"],
    "javascript": ["node"],
}


class WorkspaceUnavailable(Exception):
    pass


class WorkspaceImageNotBuilt(WorkspaceUnavailable):
    pass


def _identity(project_id: str) -> str:
    return sha256(project_id.encode("utf-8")).hexdigest()[:32]


def container_name(project_id: str) -> str:
    return f"webide_workspace_{_identity(project_id)}"


def volume_name(project_id: str) -> str:
    return f"webide_workspace_data_{_identity(project_id)}"


def _client():
    try:
        return docker.from_env()
    except DockerException as error:
        raise WorkspaceUnavailable() from error


def _get_container(client, project_id: str, user_id: str):
    try:
        container = client.containers.get(container_name(project_id))
    except NotFound:
        return None
    except DockerException as error:
        raise WorkspaceUnavailable() from error
    labels = container.labels or {}
    if labels.get("webide.project_id") != project_id or labels.get("webide.user_id") != user_id:
        logger.error("Workspace label mismatch for project %s", project_id)
        return None
    return container


def _require_local_image(client) -> None:
    """Fail clearly before containers.run can fall back to a registry pull."""
    try:
        client.images.get(WORKSPACE_IMAGE)
    except ImageNotFound as error:
        raise WorkspaceImageNotBuilt(
            f"Web IDE Docker image {WORKSPACE_IMAGE} is not available. Build the image before starting a workspace."
        ) from error
    except DockerException as error:
        raise WorkspaceUnavailable() from error


def _archive(files: list[dict]) -> io.BytesIO:
    import tarfile

    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        for file in files:
            path = file["path"]
            content = file.get("content", "").encode("utf-8")
            info = tarfile.TarInfo(path)
            info.size = len(content)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(content))
    data.seek(0)
    return data


def _sync_files(container, files: list[dict]) -> None:
    if not container.put_archive("/workspace", _archive(files)):
        raise WorkspaceUnavailable()


def _run_exec(container, command: list[str]):
    """Run an explicit command in the persistent workspace, bypassing ENTRYPOINT."""
    return container.exec_run(command, workdir="/workspace", user="1000:1000", demux=True)


def _decode_output(result) -> tuple[str, str]:
    stdout, stderr = result.output or (b"", b"")
    return (
        (stdout or b"").decode("utf-8", "replace"),
        (stderr or b"").decode("utf-8", "replace"),
    )


def _execution_commands(file_path: str, language: str) -> list[list[str]]:
    """Return explicit in-container compiler/runtime commands for a source file."""
    if language in LANGUAGE_COMMANDS:
        return [[*LANGUAGE_COMMANDS[language], file_path]]
    if language == "java":
        class_name = file_path.rsplit("/", 1)[-1].removesuffix(".java")
        return [["javac", file_path], ["java", class_name]]
    if language == "cpp":
        return [["g++", file_path, "-o", "main"], ["./main"]]
    raise ValueError(f"Unsupported execution language: {language}")
    # put_archive writes as root. Terminal sessions remain unprivileged.
    result = container.exec_run(["chown", "-R", "1000:1000", "/workspace"])
    if result.exit_code != 0:
        raise WorkspaceUnavailable()


def start_workspace(project_id: str, user_id: str, files: list[dict]) -> str:
    client = _client()
    _require_local_image(client)
    container = _get_container(client, project_id, user_id)
    try:
        if container is None:
            try:
                volume = client.volumes.get(volume_name(project_id))
                if (volume.attrs.get("Labels") or {}).get("webide.user_id") != user_id:
                    raise WorkspaceUnavailable()
            except NotFound:
                client.volumes.create(volume_name(project_id), labels={"webide.project_id": project_id, "webide.user_id": user_id})
            container = client.containers.run(
                WORKSPACE_IMAGE,
                name=container_name(project_id),
                detach=True,
                labels={"webide.project_id": project_id, "webide.user_id": user_id},
                volumes={volume_name(project_id): {"bind": "/workspace", "mode": "rw"}},
                network_mode=os.getenv("WORKSPACE_NETWORK_MODE", "bridge"),
                read_only=True,
                tmpfs={"/tmp": "rw,noexec,nosuid,size=128m", "/var/tmp": "rw,noexec,nosuid,size=128m"},
                mem_limit=os.getenv("WORKSPACE_MEMORY_LIMIT", "512m"),
                nano_cpus=int(float(os.getenv("WORKSPACE_CPU_LIMIT", "1.0")) * 1_000_000_000),
                pids_limit=int(os.getenv("WORKSPACE_PIDS_LIMIT", "128")),
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                user="0:0",
                working_dir="/workspace",
            )
            _sync_files(container, files)
        elif container.status != "running":
            container.start()
        return "running"
    except DockerException as error:
        logger.exception("Could not start workspace for project %s", project_id)
        raise WorkspaceUnavailable() from error


def workspace_status(project_id: str, user_id: str) -> str:
    container = _get_container(_client(), project_id, user_id)
    return "stopped" if container is None else container.status


def stop_workspace(project_id: str, user_id: str) -> str:
    container = _get_container(_client(), project_id, user_id)
    if container and container.status == "running":
        try:
            container.stop(timeout=10)
        except DockerException as error:
            raise WorkspaceUnavailable() from error
    return "stopped"


def restart_workspace(project_id: str, user_id: str, files: list[dict]) -> str:
    stop_workspace(project_id, user_id)
    return start_workspace(project_id, user_id, files)


def sync_workspace_file(project_id: str, user_id: str, file: dict) -> None:
    container = _get_container(_client(), project_id, user_id)
    if container is None or container.status != "running":
        return
    _sync_files(container, [file])


def run_workspace_file(project_id: str, user_id: str, files: list[dict], file_path: str, language: str, code: str) -> dict:
    started = time.monotonic()
    try:
        start_workspace(project_id, user_id, files)
        # Resolve the persistent container by this project's labels/name; never
        # create a per-execution container (which would invoke its ENTRYPOINT).
        container = _get_container(_client(), project_id, user_id)
        if container is None or container.status != "running":
            raise WorkspaceUnavailable()
        _sync_files(container, [{"path": file_path, "content": code}])
        stdout_parts, stderr_parts = [], []
        exit_code = 0
        for command in _execution_commands(file_path, language):
            result = _run_exec(container, command)
            stdout, stderr = _decode_output(result)
            stdout_parts.append(stdout)
            stderr_parts.append(stderr)
            exit_code = result.exit_code
            if exit_code != 0:
                break
        return {
            "status": "success" if exit_code == 0 else "error",
            "stdout": "".join(stdout_parts),
            "stderr": "".join(stderr_parts),
            "exit_code": exit_code,
            "execution_time_ms": int((time.monotonic() - started) * 1000),
        }
    except DockerException as error:
        raise WorkspaceUnavailable() from error


def open_terminal_socket(project_id: str, user_id: str, files: list[dict]):
    start_workspace(project_id, user_id, files)
    client = _client()
    container = _get_container(client, project_id, user_id)
    try:
        created = client.api.exec_create(
            container.id,
            ["bash", "--login", "-i"],
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            workdir="/workspace",
            user="1000:1000",
            environment={"HOME": "/home/developer", "TERM": "xterm-256color"},
        )
        return client.api.exec_start(created["Id"], socket=True, tty=True)
    except DockerException as error:
        raise WorkspaceUnavailable() from error
