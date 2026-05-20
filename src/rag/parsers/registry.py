from __future__ import annotations

import re
from llama_index.core.schema import TextNode

from src.rag.parsers.base import BaseParser
from src.rag.errors import UnsupportedContentTypeError


class ParserRegistry:
    """Strategy-registry: maps content-type strings to BaseParser instances."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}
        self._variants: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        self._parsers[parser.content_type] = parser
        for variant in parser.variants:
            if variant.startswith("+"):
                self._variants[parser.content_type + variant] = parser
            else:
                self._parsers[variant] = parser

    def get(self, content_type: str) -> BaseParser:
        if content_type in self._parsers:
            return self._parsers[content_type]
        if content_type in self._variants:
            return self._variants[content_type]
        if "+" in content_type:
            base = content_type.split("+", 1)[0]
            if base in self._parsers:
                return self._parsers[base]
        raise UnsupportedContentTypeError(content_type)

    @property
    def supported_types(self) -> list[str]:
        types = list(self._parsers.keys())
        types.extend(self._variants.keys())
        return sorted(types)


# ---------------------------------------------------------------------------
# Post-processing functions (not part of parser strategy)
# ---------------------------------------------------------------------------


def clean_nodes(nodes: list[TextNode]) -> list[TextNode]:
    seen: set[str] = set()
    cleaned: list[TextNode] = []
    for node in nodes:
        text = re.sub(r"\s+", " ", node.text).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(TextNode(text=text, metadata=node.metadata))
    return cleaned


def chunk_nodes(
    nodes: list[TextNode], chunk_size: int = 512, overlap: int = 50
) -> list[TextNode]:
    result: list[TextNode] = []
    for node in nodes:
        text = node.text
        tokens = text.split()
        token_count = len(tokens)

        if token_count <= chunk_size:
            result.append(node)
            continue

        paragraphs = re.split(r"\n\n+", text)
        current_parts: list[str] = []
        current_len = 0

        for para in paragraphs:
            para_tokens = len(para.split())
            if current_len + para_tokens > chunk_size and current_parts:
                result.append(
                    TextNode(
                        text="\n\n".join(current_parts),
                        metadata={**node.metadata, "token_count": current_len},
                    )
                )
                current_parts = [para]
                current_len = para_tokens
            else:
                current_parts.append(para)
                current_len += para_tokens

        if current_parts:
            result.append(
                TextNode(
                    text="\n\n".join(current_parts),
                    metadata={**node.metadata, "token_count": current_len},
                )
            )

    return result


# Global singleton
registry = ParserRegistry()
