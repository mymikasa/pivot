import anyio

from llama_index.core.schema import TextNode

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext
from src.pipeline.executor import PipelineExecutor


class AppendStep(PipelineStep):
    def __init__(self, text: str) -> None:
        self.text = text

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.nodes.append(TextNode(text=self.text))
        return ctx


def test_executor_runs_steps_and_reports_progress():
    progress: list[int] = []
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
    )
    executor = PipelineExecutor([AppendStep("a"), AppendStep("b")])

    result = anyio.run(executor.execute, ctx, progress.append)

    assert [node.text for node in result.nodes] == ["a", "b"]
    assert progress == [50, 100]
