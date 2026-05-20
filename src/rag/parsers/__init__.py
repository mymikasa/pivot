from src.rag.parsers.registry import ParserRegistry, clean_nodes, chunk_nodes, registry
from src.rag.parsers.base import BaseParser, ParseResult

# Import parser modules so they're available for registration
from src.rag.parsers import text as _text
from src.rag.parsers import json_parser as _json_parser
from src.rag.parsers import html as _html
from src.rag.parsers import markdown as _markdown
from src.rag.parsers import pdf as _pdf
from src.rag.parsers import docx as _docx

# Register all built-in parsers
registry.register(_text.TextParser())
registry.register(_json_parser.JsonParser())
registry.register(_html.HtmlParser())
registry.register(_markdown.MarkdownParser())
registry.register(_pdf.PdfParser())
registry.register(_docx.DocxParser())

# Backward-compatible alias
PARSERS = registry

__all__ = [
    "registry",
    "ParserRegistry",
    "BaseParser",
    "ParseResult",
    "PARSERS",
    "clean_nodes",
    "chunk_nodes",
]
