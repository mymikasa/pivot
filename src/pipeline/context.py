from dataclasses import dataclass, field
from typing import Any

from llama_index.core.schema import TextNode


@dataclass
class PipelineContext:
    kb_id: int
    document_id: int
    object_key: str
    content_type: str
    raw_binary: bytes
    nodes: list[TextNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
