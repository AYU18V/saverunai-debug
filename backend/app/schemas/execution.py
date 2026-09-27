from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.project import normalize_file_path

class ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    file_path: str = Field(max_length=255)
    language: str
    code: str
    @field_validator("file_path")
    @classmethod
    def path(cls, value): return normalize_file_path(value)
    @field_validator("language")
    @classmethod
    def language_ok(cls, value):
        if value not in {"python", "javascript", "java", "cpp"}: raise ValueError("Unsupported language")
        return value

class ExecutionResponse(BaseModel):
    status: str; stdout: str = ""; stderr: str = ""; exit_code: int | None = None; execution_time_ms: int = 0
