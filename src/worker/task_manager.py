from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.parse_task import ParseTask, ParseTaskStatus


class TaskManager:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(
        self,
        *,
        kb_id: int,
        document_id: int,
        object_key: str,
        content_type: str,
    ) -> ParseTask:
        task = ParseTask(
            kb_id=kb_id,
            document_id=document_id,
            object_key=object_key,
            content_type=content_type,
            status=ParseTaskStatus.PENDING.value,
            progress=0,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: int) -> ParseTask | None:
        return self.db.get(ParseTask, task_id)

    def list_tasks(
        self,
        *,
        kb_id: int | None = None,
        document_id: int | None = None,
    ) -> list[ParseTask]:
        query = self.db.query(ParseTask)
        if kb_id is not None:
            query = query.filter(ParseTask.kb_id == kb_id)
        if document_id is not None:
            query = query.filter(ParseTask.document_id == document_id)
        return query.order_by(ParseTask.id.desc()).all()

    def claim_next_pending_task(self) -> ParseTask | None:
        if self.db.get_bind().dialect.name == "sqlite":
            task = (
                self.db.query(ParseTask)
                .filter(ParseTask.status == ParseTaskStatus.PENDING.value)
                .order_by(ParseTask.id.asc())
                .first()
            )
            if task is None:
                return None
        else:
            row = self.db.execute(
                text(
                    "SELECT id FROM parse_tasks"
                    " WHERE status = :status"
                    " ORDER BY id ASC"
                    " LIMIT 1"
                    " FOR UPDATE SKIP LOCKED"
                ),
                {"status": ParseTaskStatus.PENDING.value},
            ).first()
            if row is None:
                return None
            task = self.db.get(ParseTask, row[0])

        task.status = ParseTaskStatus.RUNNING.value
        task.progress = 0
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_progress(self, task_id: int, progress: int) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.progress = max(0, min(100, progress))
        self.db.commit()

    def complete_task(self, task_id: int) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.status = ParseTaskStatus.COMPLETED.value
        task.progress = 100
        self.db.commit()

    def fail_task(self, task_id: int, message: str) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.status = ParseTaskStatus.FAILED.value
        task.error_message = message
        self.db.commit()

    def cancel_task(self, task_id: int) -> bool:
        task = self.db.get(ParseTask, task_id)
        if task is None or task.status == ParseTaskStatus.RUNNING.value:
            return False
        task.status = ParseTaskStatus.CANCELLED.value
        self.db.commit()
        return True
