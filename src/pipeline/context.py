from dataclasses import dataclass, field
from typing import Any


@dataclass
class Section:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    kb_id: int
    document_id: int
    object_key: str
    content_type: str
    raw_binary: bytes
    sections: list[Section] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
