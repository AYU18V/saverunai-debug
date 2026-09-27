from datetime import datetime
from typing import TypedDict


class ProjectFile(TypedDict):
    path: str
    content: str
    language: str


class ProjectDocument(TypedDict):
    user_id: str
    name: str
    description: str
    files: list[ProjectFile]
    created_at: datetime
    updated_at: datetime
