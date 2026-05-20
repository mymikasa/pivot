import logging

from llama_index.core.schema import BaseNode
from llama_index.core.utils import iter_batch
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.core.vector_stores.utils import node_to_metadata_dict
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.milvus.base import MILVUS_ID_FIELD
from llama_index.vector_stores.milvus.utils import BaseSparseEmbeddingFunction
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import DataType

from src.infrastructure.config import settings

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

        executor_wrapper = (
            self.client.upsert if self.upsert_mode else self.client.insert
        )
        for insert_batch in iter_batch(insert_list, self.batch_size):
            executor_wrapper(
                self.collection_name,
                insert_batch,
                partition_name=add_kwargs.get("milvus_partition_name"),
            )
        if add_kwargs.get("force_flush", False):
            self.client.flush(self.collection_name)
        return insert_ids


_cached_embedding = None
_cached_vector_store = None


def build_embedding():
    global _cached_embedding
    if _cached_embedding is not None:
        return _cached_embedding
    provider = settings.embedding_provider
    if provider == "openai":
        _cached_embedding = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            api_base=settings.embedding_api_base,
            dimensions=settings.embedding_dim,
        )
    elif provider == "huggingface":
        _cached_embedding = HuggingFaceEmbedding(
            model_name=settings.embedding_model, trust_remote_code=False
        )
    else:
        raise ValueError(f"不支持的 embedding_provider: {provider}")
    return _cached_embedding


def build_vector_store() -> BasePydanticVectorStore:
    global _cached_vector_store
    if _cached_vector_store is not None:
        return _cached_vector_store
    _cached_vector_store = PivotMilvusVectorStore(
        uri=settings.milvus_uri,
        collection_name="pivot_chunks",
        dim=settings.embedding_dim,
        overwrite=False,
        scalar_field_names=["kb_id", "document_id", "chunk_index"],
        scalar_field_types=[DataType.INT64, DataType.INT64, DataType.INT64],
    )
    return _cached_vector_store
