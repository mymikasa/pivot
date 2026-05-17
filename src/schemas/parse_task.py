from datetime import datetime

from pydantic import BaseModel, Field


class CreateParseTaskRequest(BaseModel):
    kb_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    object_key: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=128)
    filename: str | None = None
    user_id: int | None = None


class CreateParseTaskResponse(BaseModel):
    task_id: int
    status: str


class ParseTaskResponse(BaseModel):
    task_id: int
    kb_id: int
    document_id: int
    status: str
    progress: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ListParseTasksResponse(BaseModel):
    tasks: list[ParseTaskResponse]
