from collections.abc import Callable

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class PipelineExecutor:
    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps

    async def execute(
        self,
        ctx: PipelineContext,
        on_progress: Callable[[int], None] | None = None,
    ) -> PipelineContext:
        total = len(self.steps)
        for index, step in enumerate(self.steps, start=1):
            ctx = await step.execute(ctx)
            if on_progress is not None:
                on_progress(int(index / total * 100))
        return ctx
