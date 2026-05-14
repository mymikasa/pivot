from src.models.parse_task import ParseTaskStatus
from src.worker.task_manager import TaskManager
from src.worker.task_runner import run_one_task


def test_run_one_task_completes_pending_task(db):
    manager = TaskManager(db)
    task = manager.create_task(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
    )

    def download(_object_key: str) -> bytes:
        return b"hello pivot"

    def ingest_file(*_args, **_kwargs) -> int:
        return 1

    ran = run_one_task(db, download_file=download, ingest_file=ingest_file)

    refreshed = manager.get_task(task.id)
    assert ran is True
    assert refreshed is not None
    assert refreshed.status == ParseTaskStatus.COMPLETED.value
    assert refreshed.progress == 100
