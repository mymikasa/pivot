import anyio

from src.pipeline.context import PipelineContext, Section
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep


def test_clean_step_normalizes_and_deduplicates_sections():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        sections=[
            Section(text=" hello   world "),
            Section(text="hello world"),
            Section(text="second\n\nparagraph"),
        ],
    )

    result = anyio.run(CleanStep().execute, ctx)

    assert [section.text for section in result.sections] == [
        "hello world",
        "second paragraph",
    ]


def test_chunk_step_splits_text_with_overlap():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        sections=[Section(text="one two three four five six")],
    )

    result = anyio.run(ChunkStep(chunk_token_num=3, overlap=1).execute, ctx)

    assert [chunk.content for chunk in result.chunks] == [
        "one two three",
        "three four five",
        "five six",
    ]
