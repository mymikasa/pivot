import asyncio
import logging
import threading
import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.pipeline.context import PipelineContext
from src.pipeline.default_pipeline import build_default_pipeline
from src.worker.task_manager import TaskManager

logger = logging.getLogger(__name__)


def default_download_file(object_key: str) -> bytes:
    raise RuntimeError(f"尚未配置 MinIO 下载客户端，无法下载 {object_key}")


def run_one_task(
    db: Session,
    *,
    download_file: Callable[[str], bytes] = default_download_file,
) -> bool:
    manager = TaskManager(db)
    task = manager.claim_next_pending_task()
    if task is None:
        return False

    try:
        raw_binary = download_file(task.object_key)
        ctx = PipelineContext(
            kb_id=task.kb_id,
            document_id=task.document_id,
            object_key=task.object_key,
            content_type=task.content_type,
            raw_binary=raw_binary,
        )
        pipeline = build_default_pipeline(db)
        asyncio.run(
            pipeline.execute(
                ctx,
                on_progress=lambda progress: manager.update_progress(
                    task.id, progress
                ),
            )
        )
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
        poll_interval_seconds: float = settings.worker_poll_interval_seconds,
    ) -> None:
        self.session_factory = session_factory
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
                did_work = run_one_task(db)
            if not did_work:
                time.sleep(self.poll_interval_seconds)
