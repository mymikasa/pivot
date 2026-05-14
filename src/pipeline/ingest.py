import logging

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.utils import iter_batch
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.core.vector_stores.utils import node_to_metadata_dict
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.milvus.base import MILVUS_ID_FIELD
from llama_index.vector_stores.milvus.utils import BaseSparseEmbeddingFunction
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import DataType
from sqlalchemy.orm import Session

from src.core.config import settings
from src.pipeline.context import Chunk as PipelineChunk
from src.pipeline.context import PipelineContext
from src.pipeline.parsers import PARSERS, clean_sections, chunk_sections
from src.pipeline.steps.store_step import persist_document_chunks

logger = logging.getLogger(__name__)


class PivotMilvusVectorStore(MilvusVectorStore):
    def add(self, nodes: list[BaseNode], **add_kwargs) -> list[str]:
        insert_list = []
        insert_ids = []

        for node in nodes:
            entry = node_to_metadata_dict(
                node, remove_text=True, text_field=self.text_key
            )
            if "pivot_document_id" in entry:
                entry["document_id"] = entry.pop("pivot_document_id")
            entry[self.text_key] = node.dict()[self.text_key]
            entry[MILVUS_ID_FIELD] = node.node_id
            if self.enable_dense:
                entry[self.embedding_field] = node.embedding
            if self.enable_sparse and isinstance(
                self.sparse_embedding_function, BaseSparseEmbeddingFunction
            ):
                entry[self.sparse_embedding_field] = (
                    self.sparse_embedding_function.encode_documents([node.text])[0]
                )

            insert_ids.append(node.node_id)
            insert_list.append(entry)

        executor_wrapper = self.client.upsert if self.upsert_mode else self.client.insert
        for insert_batch in iter_batch(insert_list, self.batch_size):
            executor_wrapper(
                self.collection_name,
                insert_batch,
                partition_name=add_kwargs.get("milvus_partition_name"),
            )
        if add_kwargs.get("force_flush", False):
            self.client.flush(self.collection_name)
        return insert_ids


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
    return PivotMilvusVectorStore(
        uri=settings.milvus_uri,
        collection_name="pivot_chunks",
        dim=settings.embedding_dim,
        overwrite=False,
        scalar_field_names=["kb_id", "document_id", "chunk_index"],
        scalar_field_types=[DataType.INT64, DataType.INT64, DataType.INT64],
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
    filename: str | None = None,
    user_id: int | None = None,
    db: Session | None = None,
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
        "kb_id": kb_id,
        "pivot_document_id": document_id,
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

    if db is not None:
        ctx = PipelineContext(
            kb_id=kb_id,
            document_id=document_id,
            object_key=object_key,
            content_type=content_type,
            raw_binary=raw,
            chunks=[
                PipelineChunk(
                    index=chunk.index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    metadata=chunk.metadata,
                )
                for chunk in chunks
            ],
            metadata={
                "filename": filename,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "user_id": user_id,
            },
        )
        persist_document_chunks(db, ctx)

    logger.info(
        "ingest完成: kb_id=%s document_id=%s nodes=%d",
        kb_id, document_id, len(nodes),
    )
    return len(nodes)
