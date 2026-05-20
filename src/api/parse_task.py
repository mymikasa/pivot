from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_parse_user, get_db
from src.infrastructure.security import AuthenticatedUser
from src.models.parse_task import ParseTask
from src.schemas.parse_task import (
    CreateParseTaskRequest,
    CreateParseTaskResponse,
    ListParseTasksResponse,
    ParseTaskResponse,
)
from src.worker.task_manager import TaskManager

router = APIRouter(prefix="/parse/tasks", tags=["parse"])


def to_response(task: ParseTask) -> ParseTaskResponse:
    return ParseTaskResponse(
        task_id=task.id,
        kb_id=task.kb_id,
        document_id=task.document_id,
        status=task.status,
        progress=task.progress,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("", response_model=CreateParseTaskResponse)
def create_parse_task(
    body: CreateParseTaskRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
) -> CreateParseTaskResponse:
    task = TaskManager(db).create_task(
        kb_id=body.kb_id,
        document_id=body.document_id,
        object_key=body.object_key,
        content_type=body.content_type,
        filename=body.filename,
        user_id=body.user_id or _user.user_id,
    )
    return CreateParseTaskResponse(task_id=task.id, status=task.status)


@router.get("", response_model=ListParseTasksResponse)
def list_parse_tasks(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
    kb_id: Annotated[int | None, Query(gt=0)] = None,
    document_id: Annotated[int | None, Query(gt=0)] = None,
) -> ListParseTasksResponse:
    tasks = TaskManager(db).list_tasks(kb_id=kb_id, document_id=document_id)
    return ListParseTasksResponse(tasks=[to_response(task) for task in tasks])


@router.get("/{task_id}", response_model=ParseTaskResponse)
def get_parse_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
) -> ParseTaskResponse:
    task = TaskManager(db).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return to_response(task)


@router.delete("/{task_id}")
def cancel_parse_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
) -> dict[str, str]:
    if not TaskManager(db).cancel_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="任务不存在或正在运行，无法取消",
        )
    return {"message": "task cancelled"}
