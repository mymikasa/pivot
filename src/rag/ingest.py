import logging
from pathlib import PurePosixPath

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sqlalchemy.orm import Session

from src.models.document_chunk import DocumentChunk
from src.rag.parsers import registry, ParseResult, clean_nodes, chunk_nodes
from src.rag.dependencies import build_embedding, build_vector_store
from src.rag.errors import UnsupportedContentTypeError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step functions — pure, independently testable
# ---------------------------------------------------------------------------

def parse_bytes(raw: bytes, content_type: str, config: dict | None = None) -> ParseResult:
    parser = registry.get(content_type)
    return parser.parse(raw, config=config)


def clean_and_chunk(
    nodes: list[TextNode],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[TextNode]:
    nodes = clean_nodes(nodes)
    return chunk_nodes(nodes, chunk_size, chunk_overlap)


def tag_metadata(
    nodes: list[TextNode],
    *,
    kb_id: int,
    document_id: int,
    filename: str | None = None,
    content_type: str = "",
) -> list[TextNode]:
    for i, node in enumerate(nodes):
        node.metadata["kb_id"] = kb_id
        node.metadata["pivot_document_id"] = document_id
        node.metadata["chunk_index"] = i
        node.metadata["filename"] = filename or ""
        node.metadata["content_type"] = content_type
    return nodes


def embed_and_store(
    nodes: list[TextNode],
    embed_model: HuggingFaceEmbedding | OpenAIEmbedding,
    vector_store: BasePydanticVectorStore,
) -> list[str]:
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=False,
    )
    return [node.node_id for node in nodes]


def persist_chunks(
    db: Session,
    nodes: list[TextNode],
    *,
    kb_id: int,
    document_id: int,
    object_key: str,
    content_type: str,
    filename: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    user_id: int | None = None,
) -> int:
    db.query(DocumentChunk).filter(
        DocumentChunk.kb_id == kb_id,
        DocumentChunk.document_id == document_id,
    ).delete()

    resolved_filename = str(
        filename or PurePosixPath(object_key).name or object_key
    )

    for i, node in enumerate(nodes):
        meta = node.metadata
        db.add(
            DocumentChunk(
                kb_id=kb_id,
                document_id=document_id,
                chunk_index=meta.get("chunk_index", i),
                content=node.text,
                token_count=meta.get("token_count", len(node.text.split())),
                source_page=meta.get("source_page"),
                section_title=meta.get("section_title"),
                section_path=meta.get("section_path"),
                filename=resolved_filename,
                content_type=content_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                version=1,
                user_id=user_id,
            )
        )
    db.commit()
    return len(nodes)


# ---------------------------------------------------------------------------
# Pipeline class — orchestrates steps with DI-held dependencies
# ---------------------------------------------------------------------------

class IngestPipeline:
    def __init__(
        self,
        embed_model: HuggingFaceEmbedding | OpenAIEmbedding,
        vector_store: BasePydanticVectorStore,
    ):
        self.embed_model = embed_model
        self.vector_store = vector_store

    def run(
        self,
        raw: bytes,
        *,
        content_type: str,
        kb_id: int,
        document_id: int,
        object_key: str,
        db: Session | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        filename: str | None = None,
        user_id: int | None = None,
    ) -> int:
        result = parse_bytes(raw, content_type)
        nodes = result.nodes
        nodes = clean_and_chunk(nodes, chunk_size, chunk_overlap)
        if not nodes:
            return 0

        nodes = tag_metadata(
            nodes,
            kb_id=kb_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
        )

        embed_and_store(nodes, self.embed_model, self.vector_store)

        if db is not None:
            persist_chunks(
                db,
                nodes,
                kb_id=kb_id,
                document_id=document_id,
                object_key=object_key,
                content_type=content_type,
                filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                user_id=user_id,
            )

        logger.info(
            "ingest完成: kb_id=%s document_id=%s nodes=%d",
            kb_id,
            document_id,
            len(nodes),
        )
        return len(nodes)


# ---------------------------------------------------------------------------
# Backward-compatible entry point
# ---------------------------------------------------------------------------

def ingest_bytes(
    raw: bytes,
    *,
    content_type: str,
    kb_id: int,
    document_id: int,
    object_key: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    filename: str | None = None,
    user_id: int | None = None,
    db: Session | None = None,
) -> int:
    """向后兼容入口。推荐直接使用 IngestPipeline。"""
    pipeline = IngestPipeline(build_embedding(), build_vector_store())
    return pipeline.run(
        raw,
        content_type=content_type,
        kb_id=kb_id,
        document_id=document_id,
        object_key=object_key,
        db=db,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        filename=filename,
        user_id=user_id,
    )
