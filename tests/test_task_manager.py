from src.models.parse_task import ParseTaskStatus
from src.worker.task_manager import TaskManager


def test_task_manager_creates_and_lists_tasks(db):
    manager = TaskManager(db)

    task = manager.create_task(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
    )

    assert task.id is not None
    assert task.status == ParseTaskStatus.PENDING.value
    assert manager.list_tasks(kb_id=7, document_id=42)[0].id == task.id


def test_task_manager_claims_next_pending_task(db):
    manager = TaskManager(db)
    created = manager.create_task(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
    )

    claimed = manager.claim_next_pending_task()

    assert claimed is not None
    assert claimed.id == created.id
    assert claimed.status == ParseTaskStatus.RUNNING.value
    assert claimed.progress == 0
