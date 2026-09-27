from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_mongo_connection, connect_to_mongo
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.execution import router as execution_router
from app.routes.terminal import router as terminal_router
from app.routes.workspaces import router as workspaces_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(execution_router)
app.include_router(workspaces_router)
app.include_router(terminal_router)


@app.get("/")
def read_root():
    return {"message": "Web IDE AI Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
