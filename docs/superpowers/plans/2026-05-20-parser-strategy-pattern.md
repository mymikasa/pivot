# Parser Strategy Pattern Refactoring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `src/rag/parsers/` from a function-dict pattern to a strategy pattern with BaseParser/ParseResult abstractions, per-format files, and config+variant customization support.

**Architecture:** Each parser format gets its own file with a class inheriting `BaseParser`. A `ParserRegistry` singleton maps content-type strings to parser instances. `ParseResult` wraps the return value to carry metadata. Utility functions move to `utils.py`.

**Tech Stack:** Python 3.12+, LlamaIndex (TextNode, MarkdownNodeParser, PyMuPDFReader, DocxReader), dataclasses

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/rag/parsers/base.py` | `ParseResult`, `BaseParser` ABC |
| Create | `src/rag/parsers/utils.py` | `_parse_with_reader`, `extract_image_urls_with_lines`, `md_to_html`, `load_images_from_urls` |
| Create | `src/rag/parsers/text.py` | `TextParser` |
| Create | `src/rag/parsers/json_parser.py` | `JsonParser` |
| Create | `src/rag/parsers/html.py` | `HtmlParser` |
| Rewrite | `src/rag/parsers/registry.py` | `ParserRegistry` class + `clean_nodes`/`chunk_nodes` |
| Rewrite | `src/rag/parsers/markdown.py` | `MarkdownParser` (keeping `RAGFlowMarkdownParser`, `MarkdownElementExtractor`) |
| Create | `src/rag/parsers/pdf.py` | `PdfParser` |
| Create | `src/rag/parsers/docx.py` | `DocxParser` |
| Rewrite | `src/rag/parsers/__init__.py` | Import all parsers to trigger registration, export public API |
| Modify | `src/rag/ingest.py` | Adapt `parse_bytes` to use registry, return `ParseResult` |
| Delete | `src/rag/parsers/models.py` | Contains only a comment |
| Delete | `src/pipeline/steps/parser_step.py` | Deprecated parser step |
| Modify | `src/pipeline/default_pipeline.py` | Remove `ParserStep` from pipeline |
| Modify | `src/pipeline/__init__.py` | Update imports to new API |
| Modify | `tests/test_pipeline.py` | Adapt tests to `ParseResult` return type |

---

### Task 1: Create `base.py` — ParseResult + BaseParser

**Files:**
- Create: `src/rag/parsers/base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_parser_registry.py`:

```python
import pytest

from src.rag.parsers.base import BaseParser, ParseResult


def test_parse_result_default_metadata():
    result = ParseResult(nodes=[])
    assert result.metadata == {}


def test_parse_result_with_metadata():
    from llama_index.core.schema import TextNode

    nodes = [TextNode(text="hello")]
    result = ParseResult(nodes=nodes, metadata={"page_count": 5})
    assert len(result.nodes) == 1
    assert result.metadata["page_count"] == 5


def test_base_parser_is_abstract():
    with pytest.raises(TypeError):
        BaseParser()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_parse_result_default_metadata tests/test_parser_registry.py::test_parse_result_with_metadata tests/test_parser_registry.py::test_base_parser_is_abstract -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/rag/parsers/base.py tests/test_parser_registry.py
git commit -m "feat(parsers): add ParseResult and BaseParser ABC"
```

---

### Task 2: Create `utils.py` — shared helper functions

**Files:**
- Create: `src/rag/parsers/utils.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_parser_registry.py`:

```python
from src.rag.parsers.utils import extract_image_urls_with_lines, md_to_html


def test_extract_image_urls_markdown():
    text = "![alt](https://img.com/a.png)\nsome text\n![alt2](https://img.com/b.png)"
    urls = extract_image_urls_with_lines(text)
    assert len(urls) == 2
    assert urls[0]["url"] == "https://img.com/a.png"
    assert urls[0]["line"] == 0
    assert urls[1]["url"] == "https://img.com/b.png"
    assert urls[1]["line"] == 2


def test_extract_image_urls_html():
    text = '<img src="https://img.com/c.png">'
    urls = extract_image_urls_with_lines(text)
    assert any(u["url"] == "https://img.com/c.png" for u in urls)


def test_extract_image_urls_empty():
    assert extract_image_urls_with_lines("") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_extract_image_urls_markdown -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write implementation**

Move these functions from the existing `registry.py` (lines 154-246) into `utils.py`:

```python
from __future__ import annotations

import logging
import re
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image


def _parse_with_reader(
    raw: bytes, reader_cls: type, param_name: str, suffix: str
) -> list:
    from llama_index.core.schema import TextNode

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        docs = reader_cls().load_data(**{param_name: Path(tmp_path)})
        return [TextNode(text=doc.text) for doc in docs if doc.text.strip()]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def extract_image_urls_with_lines(text: str) -> list[dict[str, Any]]:
    md_img_re = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
    html_img_re = re.compile(r'src=["\\\']([^"\\\'>\\s]+)', re.IGNORECASE)
    urls: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        for url in md_img_re.findall(line):
            if (url, idx) not in seen:
                urls.append({"url": url, "line": idx})
                seen.add((url, idx))
        for url in html_img_re.findall(line):
            if (url, idx) not in seen:
                urls.append({"url": url, "line": idx})
                seen.add((url, idx))

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        newline_offsets = [m.start() for m in re.finditer(r"\n", text)] + [len(text)]
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if not src:
                continue
            tag_str = str(img_tag)
            pos = text.find(tag_str)
            if pos == -1:
                pos = max(text.find(src), 0)
            line_no = 0
            for i, off in enumerate(newline_offsets):
                if pos <= off:
                    line_no = i
                    break
            if (src, line_no) not in seen:
                urls.append({"url": src, "line": line_no})
                seen.add((src, line_no))
    except Exception as e:
        logging.error("Failed to extract image urls: {}".format(e))

    return urls


def md_to_html(sections):
    import markdown as md_lib
    from bs4 import BeautifulSoup

    if not sections:
        return []
    if isinstance(sections, str):
        text = sections
    elif isinstance(sections, list) and isinstance(sections[0], str):
        text = sections[0]
    else:
        return []
    html_content = md_lib.markdown(text)
    soup = BeautifulSoup(html_content, "html.parser")
    return soup


def load_images_from_urls(urls: list[str], cache: dict | None = None) -> tuple[list, dict]:
    import requests

    cache = cache or {}
    images: list[Image.Image] = []
    for url in urls:
        if url in cache:
            if cache[url]:
                images.append(cache[url])
            continue
        img_obj = None
        try:
            if url.startswith(("http://", "https://")):
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code == 200 and response.headers.get(
                    "Content-Type", ""
                ).startswith("image/"):
                    img_obj = Image.open(BytesIO(response.content)).convert("RGB")
            else:
                local_path = Path(url)
                if local_path.exists():
                    img_obj = Image.open(url).convert("RGB")
                else:
                    logging.warning(f"Local image file not found: {url}")
        except Exception as e:
            logging.error(f"Failed to download/open image from {url}: {e}")
        cache[url] = img_obj
        if img_obj:
            images.append(img_obj)
    return images, cache
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/rag/parsers/utils.py tests/test_parser_registry.py
git commit -m "feat(parsers): extract shared utils from registry"
```

---

### Task 3: Create individual parser files (Text, JSON, HTML)

**Files:**
- Create: `src/rag/parsers/text.py`
- Create: `src/rag/parsers/json_parser.py`
- Create: `src/rag/parsers/html.py`

- [ ] **Step 1: Write tests**

Append to `tests/test_parser_registry.py`:

```python
from src.rag.parsers.text import TextParser
from src.rag.parsers.json_parser import JsonParser
from src.rag.parsers.html import HtmlParser


def test_text_parser():
    result = TextParser().parse(b"hello world")
    assert len(result.nodes) == 1
    assert result.nodes[0].text == "hello world"
    assert result.metadata == {}


def test_json_parser():
    result = JsonParser().parse(b'{"key": "value"}')
    assert len(result.nodes) == 1
    assert "key" in result.nodes[0].text


def test_html_parser():
    html = b"<html><body><p>Hello</p><p>World</p></body></html>"
    result = HtmlParser().parse(html)
    assert len(result.nodes) == 1
    assert "Hello" in result.nodes[0].text
    assert "World" in result.nodes[0].text


def test_text_parser_content_type():
    assert TextParser.content_type == "text/plain"


def test_json_parser_content_type():
    assert JsonParser.content_type == "application/json"


def test_html_parser_content_type():
    assert HtmlParser.content_type == "text/html"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_text_parser -v`
Expected: FAIL

- [ ] **Step 3: Write `text.py`**

```python
from __future__ import annotations

from src.rag.parsers.base import BaseParser, ParseResult


class TextParser(BaseParser):
    content_type = "text/plain"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        text = raw.decode("utf-8", errors="ignore")
        return ParseResult(nodes=[self._make_node(text)])

    @staticmethod
    def _make_node(text: str):
        from llama_index.core.schema import TextNode

        return TextNode(text=text)
```

- [ ] **Step 4: Write `json_parser.py`**

```python
from __future__ import annotations

import json

from src.rag.parsers.base import BaseParser, ParseResult


class JsonParser(BaseParser):
    content_type = "application/json"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        from llama_index.core.schema import TextNode

        data = json.loads(raw.decode("utf-8"))
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return ParseResult(nodes=[TextNode(text=text)])
```

- [ ] **Step 5: Write `html.py`**

```python
from __future__ import annotations

from html.parser import HTMLParser

from src.rag.parsers.base import BaseParser, ParseResult


class HtmlParser(BaseParser):
    content_type = "text/html"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        from llama_index.core.schema import TextNode

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
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 12 passed

- [ ] **Step 7: Commit**

```bash
git add src/rag/parsers/text.py src/rag/parsers/json_parser.py src/rag/parsers/html.py tests/test_parser_registry.py
git commit -m "feat(parsers): add TextParser, JsonParser, HtmlParser"
```

---

### Task 4: Create MarkdownParser, PdfParser, DocxParser

**Files:**
- Rewrite: `src/rag/parsers/markdown.py` — wrap existing classes in `MarkdownParser(BaseParser)`
- Create: `src/rag/parsers/pdf.py`
- Create: `src/rag/parsers/docx.py`

- [ ] **Step 1: Write tests**

Append to `tests/test_parser_registry.py`:

```python
from src.rag.parsers.markdown import MarkdownParser
from src.rag.parsers.pdf import PdfParser
from src.rag.parsers.docx import DocxParser


def test_markdown_parser():
    md = b"## Title\n\nParagraph here.\n\n### Sub\n\nMore text."
    result = MarkdownParser().parse(md)
    assert len(result.nodes) > 0
    assert "Paragraph here" in result.nodes[0].text or any(
        "Paragraph here" in n.text for n in result.nodes
    )


def test_markdown_parser_variants():
    assert "text/x-markdown" in MarkdownParser.variants


def test_markdown_parser_content_type():
    assert MarkdownParser.content_type == "text/markdown"


def test_pdf_parser_content_type():
    assert PdfParser.content_type == "application/pdf"


def test_docx_parser_content_type():
    assert DocxParser.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_markdown_parser -v`
Expected: FAIL

- [ ] **Step 3: Rewrite `markdown.py`**

Keep `RAGFlowMarkdownParser` and `MarkdownElementExtractor` unchanged at the top of the file. Append the new `MarkdownParser` class:

```python
# (keep existing RAGFlowMarkdownParser and MarkdownElementExtractor classes exactly as-is)
# ... (lines 1-305 unchanged) ...

# --- New strategy-pattern wrapper ---

from __future__ import annotations
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import TextNode

from src.rag.parsers.base import BaseParser, ParseResult


class MarkdownParser(BaseParser):
    content_type = "text/markdown"
    variants = ["text/x-markdown"]

    def parse(self, raw: bytes, config: dict[str, Any] | None = None) -> ParseResult:
        text = raw.decode("utf-8", errors="ignore")
        nodes: list[TextNode] = []

        parser = MarkdownNodeParser()
        doc = Document(text=text)
        parsed_nodes = parser.get_nodes_from_documents([doc])

        for node in parsed_nodes:
            content = node.text.strip()
            if not content:
                continue
            header_path = node.metadata.get("header_path", "")
            parts = [p for p in header_path.strip("/").split("/") if p]
            section_title = parts[-1] if parts else ""
            nodes.append(
                TextNode(
                    text=content,
                    metadata={
                        "section_title": section_title,
                        "section_path": header_path,
                    },
                )
            )

        return ParseResult(nodes=nodes)
```

Note: the `from __future__ import annotations` and the new imports must go at the top of the file. The two existing class definitions remain in the middle. `MarkdownParser` goes at the bottom.

- [ ] **Step 4: Write `pdf.py`**

```python
from __future__ import annotations

from llama_index.readers.file import PyMuPDFReader

from src.rag.parsers.base import BaseParser, ParseResult
from src.rag.parsers.utils import _parse_with_reader


class PdfParser(BaseParser):
    content_type = "application/pdf"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        nodes = _parse_with_reader(raw, PyMuPDFReader, "file_path", ".pdf")
        return ParseResult(nodes=nodes, metadata={"page_count": len(nodes)})
```

- [ ] **Step 5: Write `docx.py`**

```python
from __future__ import annotations

from llama_index.readers.file import DocxReader

from src.rag.parsers.base import BaseParser, ParseResult
from src.rag.parsers.utils import _parse_with_reader


class DocxParser(BaseParser):
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def parse(self, raw: bytes, config: dict | None = None) -> ParseResult:
        nodes = _parse_with_reader(raw, DocxReader, "file", ".docx")
        return ParseResult(nodes=nodes)
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 17 passed

- [ ] **Step 7: Commit**

```bash
git add src/rag/parsers/markdown.py src/rag/parsers/pdf.py src/rag/parsers/docx.py tests/test_parser_registry.py
git commit -m "feat(parsers): add MarkdownParser, PdfParser, DocxParser"
```

---

### Task 5: Rewrite `registry.py` — ParserRegistry class

**Files:**
- Rewrite: `src/rag/parsers/registry.py`

- [ ] **Step 1: Write tests**

Append to `tests/test_parser_registry.py`:

```python
from src.rag.parsers.registry import ParserRegistry
from src.rag.parsers.base import BaseParser, ParseResult


class _FakeParser(BaseParser):
    content_type = "application/fake"
    variants = ["+special"]

    def parse(self, raw: bytes, config=None) -> ParseResult:
        from llama_index.core.schema import TextNode

        return ParseResult(nodes=[TextNode(text="fake")])


def _make_registry() -> ParserRegistry:
    reg = ParserRegistry()
    reg.register(_FakeParser())
    return reg


def test_registry_get_exact():
    reg = _make_registry()
    parser = reg.get("application/fake")
    assert isinstance(parser, _FakeParser)


def test_registry_get_variant():
    reg = _make_registry()
    parser = reg.get("application/fake+special")
    assert isinstance(parser, _FakeParser)


def test_registry_get_not_found():
    reg = _make_registry()
    with pytest.raises(UnsupportedContentTypeError):
        reg.get("application/unknown")


def test_registry_variant_fallback():
    reg = _make_registry()
    # "+other" not registered, should fall back to base type
    parser = reg.get("application/fake+other")
    assert isinstance(parser, _FakeParser)


def test_registry_supported_types():
    reg = _make_registry()
    assert "application/fake" in reg.supported_types


def test_registry_returns_same_instance():
    reg = _make_registry()
    p1 = reg.get("application/fake")
    p2 = reg.get("application/fake")
    assert p1 is p2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_registry_get_exact -v`
Expected: FAIL

- [ ] **Step 3: Rewrite `registry.py`**

Replace entire file with:

```python
from __future__ import annotations

import re
from typing import Any

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
            # variant may be a full content-type alias (e.g. "text/x-markdown")
            # or a suffix (e.g. "+invoice")
            if variant.startswith("+"):
                self._variants[parser.content_type + variant] = parser
            else:
                self._parsers[variant] = parser

    def get(self, content_type: str) -> BaseParser:
        # 1. exact match (includes full alias types like text/x-markdown)
        if content_type in self._parsers:
            return self._parsers[content_type]
        # 2. variant match (e.g. application/pdf+invoice)
        if content_type in self._variants:
            return self._variants[content_type]
        # 3. strip variant suffix and try base type
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 23 passed

- [ ] **Step 5: Commit**

```bash
git add src/rag/parsers/registry.py tests/test_parser_registry.py
git commit -m "feat(parsers): add ParserRegistry with variant support"
```

---

### Task 6: Wire up `__init__.py` — auto-register all parsers

**Files:**
- Rewrite: `src/rag/parsers/__init__.py`
- Delete: `src/rag/parsers/models.py`

- [ ] **Step 1: Write test**

Append to `tests/test_parser_registry.py`:

```python
from src.rag.parsers import registry


def test_registry_has_all_builtin_parsers():
    from src.rag.parsers import registry

    expected = [
        "text/plain",
        "application/json",
        "text/html",
        "text/markdown",
        "text/x-markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    types = registry.supported_types
    for ct in expected:
        assert ct in types, f"{ct} not in registry"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser_registry.py::test_registry_has_all_builtin_parsers -v`
Expected: FAIL (parsers not registered)

- [ ] **Step 3: Rewrite `__init__.py`**

```python
from src.rag.parsers.registry import ParserRegistry, clean_nodes, chunk_nodes, registry
from src.rag.parsers.base import BaseParser, ParseResult

# Import parser modules to trigger self-registration
from src.rag.parsers import text as _text
from src.rag.parsers import json_parser as _json_parser
from src.rag.parsers import html as _html
from src.rag.parsers import markdown as _markdown
from src.rag.parsers import pdf as _pdf
from src.rag.parsers import docx as _docx

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
```

- [ ] **Step 4: Add `registry.register()` calls to each parser file**

At the bottom of each parser file, add:

`text.py`:
```python
# At module level, after class definition:
# (registration happens via __init__.py import, not here)
```

Instead, register in `__init__.py` after imports. Add after the import block:

```python
# Register all built-in parsers
registry.register(_text.TextParser())
registry.register(_json_parser.JsonParser())
registry.register(_html.HtmlParser())
_md_parser = _markdown.MarkdownParser()
registry.register(_md_parser)
registry.register(_pdf.PdfParser())
registry.register(_docx.DocxParser())
```

This is cleaner — registration in one place, parser files have no side effects.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_parser_registry.py -v`
Expected: 24 passed

- [ ] **Step 6: Delete `models.py`**

```bash
rm src/rag/parsers/models.py
```

- [ ] **Step 7: Commit**

```bash
git add src/rag/parsers/__init__.py src/rag/parsers/text.py src/rag/parsers/json_parser.py src/rag/parsers/html.py src/rag/parsers/markdown.py src/rag/parsers/pdf.py src/rag/parsers/docx.py tests/test_parser_registry.py
git rm src/rag/parsers/models.py
git commit -m "feat(parsers): wire up auto-registration, delete models.py"
```

---

### Task 7: Adapt `ingest.py` — use new registry API

**Files:**
- Modify: `src/rag/ingest.py`

- [ ] **Step 1: Update `parse_bytes` function**

Change in `src/rag/ingest.py`:

Old (lines 12-14):
```python
from src.rag.parsers import PARSERS, clean_nodes, chunk_nodes
```

New:
```python
from src.rag.parsers import registry, ParseResult, clean_nodes, chunk_nodes
```

Old (lines 23-26):
```python
def parse_bytes(raw: bytes, content_type: str) -> list[TextNode]:
    if content_type not in PARSERS:
        raise UnsupportedContentTypeError(content_type)
    return PARSERS[content_type](raw)
```

New:
```python
def parse_bytes(raw: bytes, content_type: str, config: dict | None = None) -> ParseResult:
    parser = registry.get(content_type)
    return parser.parse(raw, config=config)
```

- [ ] **Step 2: Update `IngestPipeline.run`**

Change line 143:
```python
        nodes = parse_bytes(raw, content_type)
```
to:
```python
        result = parse_bytes(raw, content_type)
        nodes = result.nodes
```

- [ ] **Step 3: Run existing tests**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All tests pass (the tests use `parse_bytes` which now returns `ParseResult`; tests that access `nodes` directly via `parse_bytes` need updating)

- [ ] **Step 4: Update tests that use `parse_bytes` directly**

In `tests/test_pipeline.py`, update functions that call `parse_bytes` and treat the result as `list[TextNode]`:

```python
# test_parse_bytes_plain_text — change:
def test_parse_bytes_plain_text():
    result = parse_bytes(b"hello world\nline two", "text/plain")
    assert len(result.nodes) > 0
    assert all(node.text for node in result.nodes)


# test_parse_bytes_unsupported — unchanged (raises exception)

# test_clean_and_chunk — change:
def test_clean_and_chunk():
    result = parse_bytes(b"hello world " * 100, "text/plain")
    chunked = clean_and_chunk(result.nodes, chunk_size=50, chunk_overlap=10)
    assert len(chunked) >= 1
    assert all(node.text for node in chunked)


# test_clean_and_chunk_empty — change:
def test_clean_and_chunk_empty():
    result = parse_bytes(b"   \n  \n  ", "text/plain")
    chunked = clean_and_chunk(result.nodes)
    assert len(chunked) >= 0


# test_tag_metadata (both tests) — change:
def test_tag_metadata():
    result = parse_bytes(b"some content here", "text/plain")
    nodes = tag_metadata(
        result.nodes,
        kb_id=42,
        document_id=7,
        filename="test.txt",
        content_type="text/plain",
    )
    for i, node in enumerate(nodes):
        assert node.metadata["kb_id"] == 42
        assert node.metadata["pivot_document_id"] == 7
        assert node.metadata["chunk_index"] == i
        assert node.metadata["filename"] == "test.txt"
        assert node.metadata["content_type"] == "text/plain"


def test_tag_metadata_default_filename():
    result = parse_bytes(b"content", "text/plain")
    nodes = tag_metadata(result.nodes, kb_id=1, document_id=1)
    for node in nodes:
        assert node.metadata["filename"] == ""
```

- [ ] **Step 5: Run all parser + pipeline tests**

Run: `python -m pytest tests/test_parser_registry.py tests/test_pipeline.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/rag/ingest.py tests/test_pipeline.py
git commit -m "refactor(ingest): adapt parse_bytes to use registry + ParseResult"
```

---

### Task 8: Clean up deprecated pipeline code

**Files:**
- Delete: `src/pipeline/steps/parser_step.py`
- Modify: `src/pipeline/default_pipeline.py`
- Modify: `src/pipeline/__init__.py`

- [ ] **Step 1: Update `default_pipeline.py`**

Remove `ParserStep` import and usage:

```python
from sqlalchemy.orm import Session

from src.infrastructure.config import settings
from src.pipeline.executor import PipelineExecutor
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.store_step import StoreStep


def build_default_pipeline(db: Session) -> PipelineExecutor:
    return PipelineExecutor(
        [
            # ParserStep removed — parsing now handled by src.rag.parsers
            CleanStep(),
            ChunkStep(chunk_token_num=512, overlap=50),
            EmbedStep(
                api_key=settings.embedding_api_key,
                model=settings.embedding_model,
                api_base=settings.embedding_api_base,
                dim=settings.embedding_dim,
            ),
            StoreStep(db),
        ]
    )
```

- [ ] **Step 2: Update `src/pipeline/__init__.py`**

Change imports from old registry to new:

```python
import warnings

warnings.warn("src.pipeline 已废弃，请使用 src.rag 代替", DeprecationWarning, stacklevel=2)

from src.rag.parsers import registry as PARSERS
from src.rag.parsers import clean_nodes, chunk_nodes

__all__ = ["PARSERS", "clean_nodes", "chunk_nodes"]
```

- [ ] **Step 3: Delete `parser_step.py`**

```bash
rm src/pipeline/steps/parser_step.py
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/default_pipeline.py src/pipeline/__init__.py
git rm src/pipeline/steps/parser_step.py
git commit -m "cleanup: remove deprecated ParserStep, update pipeline imports"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass

- [ ] **Step 2: Verify file structure**

```bash
find src/rag/parsers/ -type f -name "*.py" | sort
```

Expected output:
```
src/rag/parsers/__init__.py
src/rag/parsers/base.py
src/rag/parsers/docx.py
src/rag/parsers/html.py
src/rag/parsers/json_parser.py
src/rag/parsers/markdown.py
src/rag/parsers/pdf.py
src/rag/parsers/registry.py
src/rag/parsers/text.py
src/rag/parsers/utils.py
```

- [ ] **Step 3: Verify no dangling imports**

```bash
python -c "from src.rag.parsers import registry, ParseResult, BaseParser, clean_nodes, chunk_nodes; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Verify backward-compatible PARSERS alias**

```bash
python -c "from src.rag.parsers import PARSERS; p = PARSERS.get('text/plain'); print(type(p).__name__)"
```
Expected: `TextParser`
