from datetime import datetime
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Project name cannot be blank")
        return name

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return value.strip()


class UpdateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        name = value.strip()
        if not name:
            raise ValueError("Project name cannot be blank")
        return name

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def require_an_update(self):
        if self.name is None and self.description is None:
            raise ValueError("Provide a project name or description to update")
        return self


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


def normalize_file_path(value: str) -> str:
    path = value.strip().replace("\\", "/")
    if not path:
        raise ValueError("File path cannot be blank")
    if path.startswith("/"):
        raise ValueError("File path must be relative")
    parts = path.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("File path is invalid")
    normalized = str(PurePosixPath(*parts))
    if len(normalized) > 255:
        raise ValueError("File path is too long")
    return normalized


class ProjectFileResponse(BaseModel):
    path: str
    content: str
    language: str


class CreateProjectFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=1_000_000)
    language: str | None = Field(default=None, max_length=50)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_file_path(value)


class UpdateProjectFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(max_length=1_000_000)
    language: str | None = Field(default=None, max_length=50)


class RenameProjectFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_path: str = Field(min_length=1, max_length=255)

    @field_validator("new_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_file_path(value)
