import anyio

from src.pipeline.context import Chunk, PipelineContext
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.parser_step import ParserStep
from src.pipeline.steps.store_step import StoreStep


def test_parser_step_parses_plain_text():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary="第一段\n\n第二段".encode(),
    )

    result = anyio.run(ParserStep().execute, ctx)

    assert [section.text for section in result.sections] == ["第一段", "第二段"]


def test_embed_step_generates_deterministic_vectors():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        chunks=[Chunk(index=0, content="hello", token_count=1)],
    )

    result = anyio.run(EmbedStep(api_key="", dim=4).execute, ctx)

    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) == 4
    assert result.embeddings[0] == anyio.run(
        EmbedStep(api_key="", dim=4).embed_text, "hello"
    )


def test_store_step_persists_chunks(db):
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        chunks=[Chunk(index=0, content="hello", token_count=1)],
        embeddings=[[0.1, 0.2, 0.3, 0.4]],
    )

    result = anyio.run(StoreStep(db).execute, ctx)

    assert result.metadata["stored_chunks"] == 1
