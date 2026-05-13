from sqlalchemy.orm import Session

from src.models.document_chunk import DocumentChunk
from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class StoreStep(PipelineStep):
    def __init__(self, db: Session) -> None:
        self.db = db

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        self.db.query(DocumentChunk).filter(
            DocumentChunk.kb_id == ctx.kb_id,
            DocumentChunk.document_id == ctx.document_id,
        ).delete()

        for chunk in ctx.chunks:
            self.db.add(
                DocumentChunk(
                    kb_id=ctx.kb_id,
                    document_id=ctx.document_id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    milvus_id=None,
                )
            )
        self.db.commit()
        ctx.metadata["stored_chunks"] = len(ctx.chunks)
        return ctx
