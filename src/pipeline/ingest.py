import logging

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import DataType

from src.core.config import settings
from src.pipeline.parsers import PARSERS, clean_sections, chunk_sections

logger = logging.getLogger(__name__)


class UnsupportedContentTypeError(ValueError):
    def __init__(self, content_type: str) -> None:
        super().__init__(f"不支持的文件格式: {content_type}")
        self.content_type = content_type


def _build_embedding():
    provider = settings.embedding_provider
    if provider == "openai":
        return OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            api_base=settings.embedding_api_base,
            dimensions=settings.embedding_dim,
        )
    if provider == "huggingface":
        return HuggingFaceEmbedding(model_name=settings.embedding_model)
    raise ValueError(f"不支持的 embedding_provider: {provider}")


def _build_vector_store() -> BasePydanticVectorStore:
    return MilvusVectorStore(
        uri=settings.milvus_uri,
        dim=settings.embedding_dim,
        overwrite=True,
        scalar_field_names=["kb_id", "doc_document_id", "chunk_index"],
        scalar_field_types=[DataType.VARCHAR, DataType.VARCHAR, DataType.INT64],
    )


def ingest_bytes(
    raw: bytes,
    *,
    content_type: str,
    kb_id: int,
    document_id: int,
    object_key: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> int:
    """解析 → 清洗 → 分块 → 向量化 → 存入 Milvus，返回写入节点数。"""
    # 1. 解析
    if content_type not in PARSERS:
        raise UnsupportedContentTypeError(content_type)
    parser = PARSERS[content_type]
    sections = parser(raw)

    # 2. 清洗
    sections = clean_sections(sections)

    # 3. 分块
    chunks = chunk_sections(sections, chunk_size, chunk_overlap)
    if not chunks:
        return 0

    # 4. 构造 TextNode
    base_metadata = {
        "kb_id": str(kb_id),
        "doc_document_id": str(document_id),
        "object_key": object_key,
        "content_type": content_type,
    }
    nodes = [
        TextNode(
            text=c.content,
            metadata={**base_metadata, **c.metadata, "chunk_index": c.index},
        )
        for c in chunks
    ]

    # 5. Embedding + 写入 Milvus
    embed_model = _build_embedding()
    vector_store = _build_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=False,
    )

    logger.info(
        "ingest完成: kb_id=%s document_id=%s nodes=%d",
        kb_id, document_id, len(nodes),
    )
    return len(nodes)
