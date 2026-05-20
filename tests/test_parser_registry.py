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
