import logging
import threading
import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.core.minio import MinIOClient
from src.pipeline.ingest import ingest_bytes
from src.worker.task_manager import TaskManager

logger = logging.getLogger(__name__)


def run_one_task(
    db: Session,
    *,
    download_file: Callable[[str], bytes],
    ingest_file: Callable[..., int] = ingest_bytes,
) -> bool:
    manager = TaskManager(db)
    task = manager.claim_next_pending_task()
    if task is None:
        return False

    try:
        manager.update_progress(task.id, 10)
        raw_binary = download_file(task.object_key)

        manager.update_progress(task.id, 30)
        node_count = ingest_file(
            raw_binary,
            content_type=task.content_type,
            kb_id=task.kb_id,
            document_id=task.document_id,
            object_key=task.object_key,
            db=db,
        )
        logger.info("任务 %s 完成，写入 %d 个节点", task.id, node_count)

        manager.update_progress(task.id, 100)
        manager.complete_task(task.id)
        return True
    except Exception as exc:
        logger.exception("解析任务执行失败", extra={"task_id": task.id})
        manager.fail_task(task.id, str(exc))
        return True


class ParseTaskWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        minio_client: MinIOClient,
        poll_interval_seconds: float = settings.worker_poll_interval_seconds,
    ) -> None:
        self.session_factory = session_factory
        self.minio_client = minio_client
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            with self.session_factory() as db:
                did_work = run_one_task(
                    db,
                    download_file=self.minio_client.download,
                )
            if not did_work:
                time.sleep(self.poll_interval_seconds)
