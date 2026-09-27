# Web IDE AI Debugger

## Requirements and startup

Docker Desktop must be running and switched to Linux containers. Build the controlled workspace image once:

```powershell
docker build -t webide-dev:1.0 -f backend/docker/webide-dev/Dockerfile .
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Workspaces and terminal

Opening a project starts `webide_workspace_<hash>` with a dedicated named Docker volume mounted at `/workspace`. MongoDB remains the persistent project store; its files are copied to a newly created workspace and the Run request copies its current Monaco buffer before executing it. Terminal modifications persist in the named volume for the workspace lifetime but do not yet refresh the MongoDB file explorer automatically.

`WS /api/terminal/{project_id}?token=<JWT>` bridges xterm.js to an unprivileged `bash` process inside that project container. The image is `webide-dev:1.0`, built from `node:22.14.0-bookworm-slim`, and includes Node/npm, Python 3.11, Git, Java 17, GCC/G++, Bash, and coreutils.

### Execution commands

The verified `webide-dev:1.0` image and its running workspace container both use `ENTRYPOINT ["docker-entrypoint.sh"]` with `CMD ["sleep", "infinity"]`. The service therefore never uses the image entrypoint for source execution or creates a disposable execution container. It executes explicit commands through Docker SDK `container.exec_run` in the project workspace container: `/usr/bin/python3.11 main.py`, `node main.js`, `javac Main.java` followed by `java Main`, and `g++ main.cpp -o main` followed by `./main`. Package commands use explicit `npm ...` execs in the same container when invoked through the terminal.

Workspace resource settings are environment-configurable: `WORKSPACE_MEMORY_LIMIT` (default `512m`), `WORKSPACE_CPU_LIMIT` (`1.0`), `WORKSPACE_PIDS_LIMIT` (`128`), `WORKSPACE_NETWORK_MODE` (`bridge`). Use `none` when package downloads are not needed. Port forwarding is intentionally not exposed yet; a future controlled `/api/workspaces/{project_id}/ports` proxy should whitelist project ports instead of publishing arbitrary host ports.

Containers use a named volume only—never a host project/home directory or Docker socket—and run with read-only root filesystem, writable `/workspace` volume and temporary filesystems, dropped capabilities, `no-new-privileges`, PID/memory/CPU limits, and no privileged mode. The FastAPI host never executes terminal commands.
