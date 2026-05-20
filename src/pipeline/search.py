import warnings

from src.rag.dependencies import build_embedding as _build_embedding
from src.rag.dependencies import build_vector_store as _build_vector_store
from src.rag.errors import RerankerUnavailableError
from src.rag.rerank import HuggingFaceReranker, Reranker, build_reranker
from src.rag.schemas import SearchResult
from src.rag.retrieval import search_chunks

warnings.warn(
    "src.pipeline.search 已废弃，请使用 src.rag 代替",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "SearchResult",
    "Reranker",
    "RerankerUnavailableError",
    "HuggingFaceReranker",
    "build_reranker",
    "search_chunks",
    "_build_embedding",
    "_build_vector_store",
]
