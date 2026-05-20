from __future__ import annotations

from llama_index.readers.file import PyMuPDFReader

from src.rag.parsers.base import BaseParser, ParseResult
from src.rag.parsers.utils import _parse_with_reader


class PdfParser(BaseParser):
    content_type = "application/pdf"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        nodes = _parse_with_reader(raw, PyMuPDFReader, "file_path", ".pdf")
        return ParseResult(nodes=nodes, metadata={"page_count": len(nodes)})
