from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from llama_index.core.schema import TextNode


@dataclass
class ParseResult:
    nodes: list[TextNode]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    content_type: str
    variants: list[str] = []

    @abstractmethod
    def parse(self, raw: bytes, config: dict[str, Any] | None = None) -> ParseResult:
        ...
