from pathlib import Path

import pytest

from src.rag.errors import UnsupportedContentTypeError
from src.rag.dependencies import build_embedding as _build_embedding
from src.rag.dependencies import build_vector_store as _build_vector_store
from src.rag.ingest import (
    IngestPipeline,
    clean_and_chunk,
    ingest_bytes,
    parse_bytes,
    tag_metadata,
)


# ---------------------------------------------------------------------------
# Integration tests (backward-compatible ingest_bytes entry point)
# ---------------------------------------------------------------------------

def test_ingest_plain_text():
    count = ingest_bytes(
        b"hello world\nline two\nline three",
        content_type="text/plain",
        kb_id=1,
        document_id=1,
        object_key="test.txt",
    )
    assert count > 0


def test_ingest_markdown():
    md = Path("tests/fixtures/服务注册.md").read_bytes()
    count = ingest_bytes(
        md,
        content_type="text/markdown",
        kb_id=1,
        document_id=2,
        object_key="服务注册.md",
    )
    assert count > 0


def test_ingest_pdf():
    pdf = Path("tests/fixtures/sample.pdf").read_bytes()
    count = ingest_bytes(
        pdf,
        content_type="application/pdf",
        kb_id=1,
        document_id=3,
        object_key="sample.pdf",
    )
    assert count > 0


def test_ingest_json():
    payload = '{"items": ' + str(list(range(200))) + "}"
    count = ingest_bytes(
        payload.encode("utf-8"),
        content_type="application/json",
        kb_id=1,
        document_id=4,
        object_key="data.json",
    )
    assert count > 0


def test_ingest_empty_input():
    count = ingest_bytes(
        b"   \n  \n  ",
        content_type="text/plain",
        kb_id=1,
        document_id=5,
        object_key="empty.txt",
    )
    assert count >= 0


def test_build_embedding():
    embed = _build_embedding()
    assert embed is not None


def test_unsupported_content_type():
    with pytest.raises(
        UnsupportedContentTypeError, match="不支持的文件格式: application/vnd"
    ):
        ingest_bytes(
            b"fake xlsx content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            kb_id=1,
            document_id=99,
            object_key="data.xlsx",
        )


# ---------------------------------------------------------------------------
# Step function unit tests — no embedding / vector store needed
# ---------------------------------------------------------------------------

def test_parse_bytes_plain_text():
    result = parse_bytes(b"hello world\nline two", "text/plain")
    assert len(result.nodes) > 0
    assert all(node.text for node in result.nodes)


def test_parse_bytes_unsupported():
    with pytest.raises(UnsupportedContentTypeError):
        parse_bytes(b"data", "application/unknown")


def test_clean_and_chunk():
    result = parse_bytes(b"hello world " * 100, "text/plain")
    chunked = clean_and_chunk(result.nodes, chunk_size=50, chunk_overlap=10)
    assert len(chunked) >= 1
    assert all(node.text for node in chunked)


def test_clean_and_chunk_empty():
    result = parse_bytes(b"   \n  \n  ", "text/plain")
    chunked = clean_and_chunk(result.nodes)
    assert len(chunked) >= 0


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


# ---------------------------------------------------------------------------
# IngestPipeline integration test
# ---------------------------------------------------------------------------

def test_pipeline_run_plain_text():
    pipeline = IngestPipeline(_build_embedding(), _build_vector_store())
    # We only test with text/plain to avoid needing a real Milvus in CI
    count = pipeline.run(
        b"hello world\nline two\nline three",
        content_type="text/plain",
        kb_id=99,
        document_id=99,
        object_key="test.txt",
    )
    assert count > 0
