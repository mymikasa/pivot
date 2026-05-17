import anyio

from llama_index.core.schema import TextNode

from src.pipeline.context import PipelineContext
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep


def test_clean_step_normalizes_and_deduplicates_nodes():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        nodes=[
            TextNode(text=" hello   world "),
            TextNode(text="hello world"),
            TextNode(text="second\n\nparagraph"),
        ],
    )

    result = anyio.run(CleanStep().execute, ctx)

    assert [node.text for node in result.nodes] == [
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
        nodes=[TextNode(text="one two three four five six")],
    )

    result = anyio.run(ChunkStep(chunk_token_num=3, overlap=1).execute, ctx)

    assert [node.text for node in result.nodes] == [
        "one two three",
        "three four five",
        "five six",
    ]
