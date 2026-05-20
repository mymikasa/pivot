from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import get_current_parse_user
from src.infrastructure.security import AuthenticatedUser
from src.rag.errors import RerankerUnavailableError
from src.rag.retrieval import search_chunks
from src.schemas.search import SearchHit, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(
    body: SearchRequest,
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
) -> SearchResponse:
    try:
        results = search_chunks(
            query=body.query,
            kb_id=body.kb_id,
            top_k=body.top_k,
            rerank=body.rerank,
            rerank_top_k=body.rerank_top_k,
        )
    except RerankerUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="reranker 未配置或不可用",
        ) from exc

    return SearchResponse(
        hits=[
            SearchHit(
                chunk_index=r.chunk_index,
                document_id=r.document_id,
                kb_id=r.kb_id,
                score=r.score,
                content=r.content,
                token_count=r.token_count,
                source_page=r.source_page,
                section_title=r.section_title,
                section_path=r.section_path,
                filename=r.filename,
                content_type=r.content_type,
            )
            for r in results
        ],
        total=len(results),
    )
