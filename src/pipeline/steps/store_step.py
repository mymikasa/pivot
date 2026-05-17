from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from src.models.document_chunk import DocumentChunk
from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class StoreStep(PipelineStep):
    def __init__(self, db: Session) -> None:
        self.db = db

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.metadata["stored_chunks"] = persist_document_chunks(self.db, ctx)
        return ctx


def persist_document_chunks(db: Session, ctx: PipelineContext) -> int:
    db.query(DocumentChunk).filter(
        DocumentChunk.kb_id == ctx.kb_id,
        DocumentChunk.document_id == ctx.document_id,
    ).delete()

    filename = str(
        ctx.metadata.get("filename")
        or PurePosixPath(ctx.object_key).name
        or ctx.object_key
    )
    chunk_size = int(ctx.metadata.get("chunk_size", 512))
    chunk_overlap = int(ctx.metadata.get("chunk_overlap", 50))
    version = int(ctx.metadata.get("version", 1))
    user_id = ctx.metadata.get("user_id")

    for i, node in enumerate(ctx.nodes):
        meta = node.metadata
        db.add(
            DocumentChunk(
                kb_id=ctx.kb_id,
                document_id=ctx.document_id,
                chunk_index=meta.get("chunk_index", i),
                content=node.text,
                token_count=meta.get("token_count", len(node.text.split())),
                source_page=meta.get("source_page"),
                section_title=meta.get("section_title"),
                section_path=meta.get("section_path"),
                filename=filename,
                content_type=ctx.content_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                version=version,
                user_id=user_id,
            )
        )
    db.commit()
    return len(ctx.nodes)
