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


# ---------------------------------------------------------------------------
# Individual parser tests
# ---------------------------------------------------------------------------

from src.rag.parsers.text import TextParser
from src.rag.parsers.json_parser import JsonParser
from src.rag.parsers.html import HtmlParser
from src.rag.parsers.markdown import MarkdownParser
from src.rag.parsers.pdf import PdfParser
from src.rag.parsers.docx import DocxParser


def test_text_parser():
    result = TextParser().parse(b"hello world")
    assert len(result.nodes) == 1
    assert result.nodes[0].text == "hello world"
    assert result.metadata == {}


def test_text_parser_content_type():
    assert TextParser.content_type == "text/plain"


def test_json_parser():
    result = JsonParser().parse(b'{"key": "value"}')
    assert len(result.nodes) == 1
    assert "key" in result.nodes[0].text


def test_json_parser_content_type():
    assert JsonParser.content_type == "application/json"


def test_html_parser():
    html = b"<html><body><p>Hello</p><p>World</p></body></html>"
    result = HtmlParser().parse(html)
    assert len(result.nodes) == 1
    assert "Hello" in result.nodes[0].text
    assert "World" in result.nodes[0].text


def test_html_parser_content_type():
    assert HtmlParser.content_type == "text/html"


def test_markdown_parser():
    md = b"## Title\n\nParagraph here.\n\n### Sub\n\nMore text."
    result = MarkdownParser().parse(md)
    assert len(result.nodes) > 0


def test_markdown_parser_variants():
    assert "text/x-markdown" in MarkdownParser.variants


def test_markdown_parser_content_type():
    assert MarkdownParser.content_type == "text/markdown"


def test_pdf_parser_content_type():
    assert PdfParser.content_type == "application/pdf"


def test_docx_parser_content_type():
    assert DocxParser.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
