import anyio

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext, Section
from src.pipeline.executor import PipelineExecutor


class AppendStep(PipelineStep):
    def __init__(self, text: str) -> None:
        self.text = text

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.sections.append(Section(text=self.text))
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

    assert [section.text for section in result.sections] == ["a", "b"]
    assert progress == [50, 100]
