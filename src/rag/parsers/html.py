from __future__ import annotations

from html.parser import HTMLParser

from llama_index.core.schema import TextNode

from src.rag.parsers.base import BaseParser, ParseResult


class HtmlParser(BaseParser):
    content_type = "text/html"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []

            def handle_data(self, data):
                if data.strip():
                    self.parts.append(data.strip())

        p = _TextExtractor()
        p.feed(raw.decode("utf-8", errors="ignore"))
        return ParseResult(nodes=[TextNode(text="\n".join(p.parts))])
