from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2048)
    kb_id: int = Field(gt=0)
    top_k: int = Field(default=5, ge=1, le=50)
    rerank: bool = False
    rerank_top_k: int | None = Field(default=None, ge=1, le=200)

    @model_validator(mode="after")
    def validate_rerank_top_k(self) -> "SearchRequest":
        if self.rerank_top_k is not None and self.rerank_top_k < self.top_k:
            raise ValueError("rerank_top_k 必须大于等于 top_k")
        return self


class SearchHit(BaseModel):
    chunk_index: int
    document_id: int
    kb_id: int
    score: float
    content: str
    token_count: int
    source_page: int | None = None
    section_title: str | None = None
    section_path: str | None = None
    filename: str
    content_type: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    total: int
