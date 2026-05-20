from __future__ import annotations

import json

from llama_index.core.schema import TextNode

from src.rag.parsers.base import BaseParser, ParseResult


class JsonParser(BaseParser):
    content_type = "application/json"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        data = json.loads(raw.decode("utf-8"))
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return ParseResult(nodes=[TextNode(text=text)])
