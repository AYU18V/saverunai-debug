from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


LANGUAGE_BY_EXTENSION = {
    ".py": "python", ".js": "javascript", ".java": "java", ".cpp": "cpp", ".c": "c",
    ".html": "html", ".css": "css", ".json": "json", ".md": "markdown",
}


class FileAlreadyExistsError(Exception):
    pass


def language_for_path(path: str) -> str:
    return LANGUAGE_BY_EXTENSION.get("." + path.rsplit(".", 1)[-1].lower() if "." in path else "", "plaintext")


def project_response(project: dict) -> dict:
    return {
        "id": str(project["_id"]),
        "name": project["name"],
        "description": project["description"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
    }


async def create_project(
    database: AsyncIOMotorDatabase, *, user_id: str, name: str, description: str
) -> dict:
    now = datetime.now(timezone.utc)
    project = {
        "user_id": user_id,
        "name": name,
        "description": description,
        "files": [{"path": "main.py", "content": 'print("Hello, World!")', "language": "python"}],
        "created_at": now,
        "updated_at": now,
    }
    result = await database.projects.insert_one(project)
    project["_id"] = result.inserted_id
    return project


async def get_projects(database: AsyncIOMotorDatabase, *, user_id: str) -> list[dict]:
    return await database.projects.find({"user_id": user_id}).sort("updated_at", -1).to_list(length=None)


async def get_project(database: AsyncIOMotorDatabase, *, project_id: str, user_id: str) -> dict | None:
    if not ObjectId.is_valid(project_id):
        return None
    return await database.projects.find_one({"_id": ObjectId(project_id), "user_id": user_id})


async def update_project(
    database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, updates: dict
) -> dict | None:
    if not ObjectId.is_valid(project_id):
        return None
    updates["updated_at"] = datetime.now(timezone.utc)
    return await database.projects.find_one_and_update(
        {"_id": ObjectId(project_id), "user_id": user_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )


async def delete_project(database: AsyncIOMotorDatabase, *, project_id: str, user_id: str) -> bool:
    if not ObjectId.is_valid(project_id):
        return False
    result = await database.projects.delete_one({"_id": ObjectId(project_id), "user_id": user_id})
    return result.deleted_count == 1


async def get_project_files(database: AsyncIOMotorDatabase, *, project_id: str, user_id: str) -> list[dict] | None:
    project = await get_project(database, project_id=project_id, user_id=user_id)
    return None if project is None else project.get("files", [])


async def get_project_file(
    database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, path: str
) -> dict | None:
    files = await get_project_files(database, project_id=project_id, user_id=user_id)
    if files is None:
        return None
    return next((file for file in files if file["path"] == path), None)


async def create_project_file(
    database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, path: str, content: str, language: str | None
) -> dict | None:
    project = await get_project(database, project_id=project_id, user_id=user_id)
    if project is None:
        return None
    if any(file["path"] == path for file in project.get("files", [])):
        raise FileAlreadyExistsError
    file = {"path": path, "content": content, "language": language or language_for_path(path)}
    updated = await database.projects.find_one_and_update(
        {"_id": project["_id"], "user_id": user_id, "files.path": {"$ne": path}},
        {"$push": {"files": file}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise FileAlreadyExistsError
    return file


async def update_project_file(
    database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, path: str, content: str, language: str | None
) -> dict | None:
    if not ObjectId.is_valid(project_id):
        return None
    updates = {"files.$.content": content, "updated_at": datetime.now(timezone.utc)}
    if language is not None:
        updates["files.$.language"] = language
    project = await database.projects.find_one_and_update(
        {"_id": ObjectId(project_id), "user_id": user_id, "files.path": path},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if project is None:
        return None
    return next(file for file in project["files"] if file["path"] == path)


async def rename_project_file(
    database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, path: str, new_path: str
) -> dict | None:
    if not ObjectId.is_valid(project_id):
        return None
    project = await get_project(database, project_id=project_id, user_id=user_id)
    if project is None or not any(file["path"] == path for file in project.get("files", [])):
        return None
    if any(file["path"] == new_path for file in project.get("files", [])):
        raise FileAlreadyExistsError
    updated = await database.projects.find_one_and_update(
        {"_id": project["_id"], "user_id": user_id, "$and": [{"files.path": path}, {"files.path": {"$ne": new_path}}]},
        {"$set": {"files.$.path": new_path, "files.$.language": language_for_path(new_path), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise FileAlreadyExistsError
    return next(file for file in updated["files"] if file["path"] == new_path)


async def delete_project_file(database: AsyncIOMotorDatabase, *, project_id: str, user_id: str, path: str) -> bool:
    if not ObjectId.is_valid(project_id):
        return False
    result = await database.projects.update_one(
        {"_id": ObjectId(project_id), "user_id": user_id, "files.path": path},
        {"$pull": {"files": {"path": path}}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count == 1
