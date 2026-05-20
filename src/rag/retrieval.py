import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import logging

from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

from src.rag.dependencies import build_embedding, build_vector_store
from src.rag.rerank import build_reranker, resolve_retrieval_top_k
from src.rag.schemas import SearchResult

logger = logging.getLogger(__name__)


def search_chunks(
    query: str,
    kb_id: int,
    *,
    top_k: int = 5,
    rerank: bool = False,
    rerank_top_k: int | None = None,
) -> list[SearchResult]:
    retrieval_top_k = resolve_retrieval_top_k(
        top_k=top_k,
        rerank=rerank,
        rerank_top_k=rerank_top_k,
    )

    embed_model = build_embedding()
    vector_store = build_vector_store()

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
        results.append(
            SearchResult(
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
            )
        )

    if not rerank:
        return results

    reranker = build_reranker()
    return reranker.rerank(query, results)[:top_k]
