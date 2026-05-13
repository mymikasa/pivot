from pathlib import Path

import pytest

from src.pipeline.ingest import _build_embedding, ingest_bytes


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
    payload = '{"items": ' + str(list(range(200))) + '}'
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
