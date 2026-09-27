import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Open the one application-level MongoDB connection and create indexes."""
    global _client, _database
    uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE", "web_ide_ai")
    if not uri:
        raise RuntimeError("MONGODB_URI is not configured")
    _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    await _client.admin.command("ping")
    _database = _client[database_name]
    await _database.users.create_index("email", unique=True, name="unique_email")
    await _database.projects.create_index(
        [("user_id", 1), ("updated_at", -1)],
        name="projects_by_user_and_updated_at",
    )


async def close_mongo_connection() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not connected")
    return _database
