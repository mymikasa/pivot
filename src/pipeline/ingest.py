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
from pathlib import PurePosixPath
from pymilvus import DataType
from sqlalchemy.orm import Session

from src.core.config import settings
from src.models.document_chunk import DocumentChunk
from src.pipeline.parsers import PARSERS, clean_nodes, chunk_nodes

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


def _persist_nodes(
    db: Session,
    nodes: list[TextNode],
    *,
    kb_id: int,
    document_id: int,
    object_key: str,
    content_type: str,
    metadata: dict,
) -> int:
    db.query(DocumentChunk).filter(
        DocumentChunk.kb_id == kb_id,
        DocumentChunk.document_id == document_id,
    ).delete()

    filename = str(
        metadata.get("filename")
        or PurePosixPath(object_key).name
        or object_key
    )
    chunk_size = int(metadata.get("chunk_size", 512))
    chunk_overlap = int(metadata.get("chunk_overlap", 50))
    version = int(metadata.get("version", 1))
    user_id = metadata.get("user_id")

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
                filename=filename,
                content_type=content_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                version=version,
                user_id=user_id,
            )
        )
    db.commit()
    return len(nodes)


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
    """解析 → 清洗 → 分块 → 向量化 → 存入 Milvus + MySQL，返回写入节点数。"""
    # 1. 解析 → TextNode
    if content_type not in PARSERS:
        raise UnsupportedContentTypeError(content_type)
    nodes = PARSERS[content_type](raw)

    # 2. 清洗
    nodes = clean_nodes(nodes)

    # 3. 分块
    nodes = chunk_nodes(nodes, chunk_size, chunk_overlap)
    if not nodes:
        return 0

    # 4. 注入 metadata（Milvus 过滤 + 检索时可直接返回）
    for i, node in enumerate(nodes):
        node.metadata["kb_id"] = kb_id
        node.metadata["pivot_document_id"] = document_id
        node.metadata["chunk_index"] = i
        node.metadata["filename"] = filename or ""
        node.metadata["content_type"] = content_type

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

    # 6. 写入 MySQL
    if db is not None:
        _persist_nodes(
            db,
            nodes,
            kb_id=kb_id,
            document_id=document_id,
            object_key=object_key,
            content_type=content_type,
            metadata={
                "filename": filename,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "user_id": user_id,
            },
        )

    logger.info(
        "ingest完成: kb_id=%s document_id=%s nodes=%d",
        kb_id, document_id, len(nodes),
    )
    return len(nodes)
