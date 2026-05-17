import anyio

from llama_index.core.schema import TextNode

from src.pipeline.context import PipelineContext
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.parser_step import ParserStep
from src.pipeline.steps.store_step import StoreStep
from src.models.document_chunk import DocumentChunk


def test_parser_step_parses_plain_text():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary="第一段\n\n第二段".encode(),
    )

    result = anyio.run(ParserStep().execute, ctx)

    assert [node.text for node in result.nodes] == ["第一段", "第二段"]


def test_embed_step_generates_deterministic_vectors():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        nodes=[TextNode(text="hello")],
    )

    result = anyio.run(EmbedStep(api_key="", dim=4).execute, ctx)

    assert len(result.nodes) == 1
    assert len(result.nodes[0].embedding) == 4
    expected = anyio.run(EmbedStep(api_key="", dim=4).embed_text, "hello")
    assert result.nodes[0].embedding == expected


def test_store_step_persists_nodes(db):
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        nodes=[
            TextNode(
                text="hello",
                metadata={
                    "token_count": 1,
                    "source_page": 2,
                    "section_title": "标题",
                    "section_path": "父级 > 标题",
                },
            )
        ],
        metadata={
            "filename": "a.txt",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "user_id": 7,
        },
    )

    result = anyio.run(StoreStep(db).execute, ctx)

    assert result.metadata["stored_chunks"] == 1
    row = db.query(DocumentChunk).one()
    assert row.source_page == 2
    assert row.section_title == "标题"
    assert row.section_path == "父级 > 标题"
    assert row.filename == "a.txt"
    assert row.content_type == "text/plain"
    assert row.chunk_size == 512
    assert row.chunk_overlap == 50
    assert row.user_id == 7
