from dataclasses import dataclass

from pydantic import BaseModel, Field


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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatSource(BaseModel):
    content: str
    score: float
    filename: str
    chunk_index: int


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)
    kb_id: int = Field(gt=0)
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=50)


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []
