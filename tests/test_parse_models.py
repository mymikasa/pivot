from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base
from src.models.document_chunk import DocumentChunk
from src.models.parse_task import ParseTask, ParseTaskStatus


def test_parse_task_and_chunk_models_can_persist():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    task = ParseTask(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
        status=ParseTaskStatus.PENDING.value,
    )
    session.add(task)
    session.commit()

    chunk = DocumentChunk(
        kb_id=7,
        document_id=42,
        chunk_index=0,
        content="hello pivot",
        token_count=2,
        milvus_id=1001,
    )
    session.add(chunk)
    session.commit()

    assert task.id is not None
    assert chunk.id is not None
    assert session.query(ParseTask).count() == 1
    assert session.query(DocumentChunk).count() == 1
