import logging
from dataclasses import replace
from typing import Protocol

from src.infrastructure.config import settings
from src.rag.errors import RerankerUnavailableError
from src.rag.schemas import SearchResult

logger = logging.getLogger(__name__)

DEFAULT_RERANK_CANDIDATE_MULTIPLIER = 5
DEFAULT_RERANK_CANDIDATE_LIMIT = 50


class Reranker(Protocol):
    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """根据查询对候选结果重新排序。"""


try:
    from sentence_transformers import CrossEncoder as _CrossEncoder
except ImportError:
    _CrossEncoder = None


_cached_reranker: Reranker | None = None


class HuggingFaceReranker:
    def __init__(self, model_name: str, device: str = "cpu"):
        if _CrossEncoder is None:
            raise RerankerUnavailableError("sentence-transformers 未安装")
        self._model = _CrossEncoder(model_name, device=device, local_files_only=True)

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return results
        pairs = [(query, r.content) for r in results]
        scores = self._model.predict(pairs)
        paired = sorted(zip(scores.tolist(), results), key=lambda x: x[0], reverse=True)
        return [replace(r, score=s) for s, r in paired]


def build_reranker() -> Reranker:
    global _cached_reranker
    if _cached_reranker is not None:
        return _cached_reranker

    provider = settings.reranker_provider.strip()
    if not provider:
        raise RerankerUnavailableError("reranker 未配置")
    if provider == "huggingface":
        _cached_reranker = HuggingFaceReranker(
            model_name=settings.reranker_model or "BAAI/bge-reranker-v2-m3",
            device="cpu",
        )
        return _cached_reranker
    raise RerankerUnavailableError(f"不支持的 reranker_provider: {provider}")


def resolve_retrieval_top_k(
    *,
    top_k: int,
    rerank: bool,
    rerank_top_k: int | None,
) -> int:
    if not rerank:
        return top_k
    if rerank_top_k is not None:
        return rerank_top_k
    return min(
        top_k * DEFAULT_RERANK_CANDIDATE_MULTIPLIER,
        DEFAULT_RERANK_CANDIDATE_LIMIT,
    )
