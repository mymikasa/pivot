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
