from __future__ import annotations

from llama_index.core.schema import TextNode

from src.rag.parsers.base import BaseParser, ParseResult


class TextParser(BaseParser):
    content_type = "text/plain"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        text = raw.decode("utf-8", errors="ignore")
        return ParseResult(nodes=[TextNode(text=text)])
