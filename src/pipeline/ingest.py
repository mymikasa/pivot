import warnings

from src.rag.dependencies import build_embedding as _build_embedding
from src.rag.dependencies import build_vector_store as _build_vector_store
from src.rag.dependencies import PivotMilvusVectorStore
from src.rag.errors import UnsupportedContentTypeError
from src.rag.ingest import ingest_bytes

warnings.warn(
    "src.pipeline.ingest 已废弃，请使用 src.rag 代替",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "UnsupportedContentTypeError",
    "PivotMilvusVectorStore",
    "_build_embedding",
    "_build_vector_store",
    "ingest_bytes",
]
