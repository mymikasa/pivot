from __future__ import annotations

from llama_index.readers.file import DocxReader

from src.rag.parsers.base import BaseParser, ParseResult
from src.rag.parsers.utils import _parse_with_reader


class DocxParser(BaseParser):
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        nodes = _parse_with_reader(raw, DocxReader, "file", ".docx")
        return ParseResult(nodes=nodes)
