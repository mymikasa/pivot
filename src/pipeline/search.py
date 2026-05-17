import logging
from dataclasses import dataclass
from typing import Protocol

from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

from src.core.config import settings
from src.pipeline.ingest import _build_embedding, _build_vector_store

logger = logging.getLogger(__name__)

DEFAULT_RERANK_CANDIDATE_MULTIPLIER = 5
DEFAULT_RERANK_CANDIDATE_LIMIT = 50


@dataclass
class SearchResult:
    chunk_index: int
    document_id: int
    kb_id: int
    score: float
    content: str
    token_count: int
    source_page: int | None
    section_title: str | None
    section_path: str | None
    filename: str
    content_type: str


class Reranker(Protocol):
    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """根据查询对候选结果重新排序。"""


class RerankerUnavailableError(RuntimeError):
    pass


def build_reranker() -> Reranker:
    provider = settings.reranker_provider.strip()
    if not provider:
        raise RerankerUnavailableError("reranker 未配置")
    raise RerankerUnavailableError(f"不支持的 reranker_provider: {provider}")


def _resolve_retrieval_top_k(
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


def search_chunks(
    query: str,
    kb_id: int,
    *,
    top_k: int = 5,
    rerank: bool = False,
    rerank_top_k: int | None = None,
) -> list[SearchResult]:
    retrieval_top_k = _resolve_retrieval_top_k(
        top_k=top_k,
        rerank=rerank,
        rerank_top_k=rerank_top_k,
    )

    embed_model = _build_embedding()
    vector_store = _build_vector_store()

    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )

    retriever = index.as_retriever(
        similarity_top_k=retrieval_top_k,
        filters=MetadataFilters(
            filters=[MetadataFilter(key="kb_id", value=kb_id)],
        ),
    )

    nodes_with_scores = retriever.retrieve(query)

    results: list[SearchResult] = []
    for nws in nodes_with_scores:
        meta = nws.node.metadata
        results.append(SearchResult(
            chunk_index=int(meta.get("chunk_index", 0)),
            document_id=int(meta.get("pivot_document_id", 0)),
            kb_id=int(meta.get("kb_id", kb_id)),
            score=nws.score or 0.0,
            content=nws.node.text,
            token_count=int(meta.get("token_count", len(nws.node.text.split()))),
            source_page=meta.get("source_page"),
            section_title=meta.get("section_title"),
            section_path=meta.get("section_path"),
            filename=meta.get("filename", ""),
            content_type=meta.get("content_type", ""),
        ))

    if not rerank:
        return results

    reranker = build_reranker()
    return reranker.rerank(query, results)[:top_k]
