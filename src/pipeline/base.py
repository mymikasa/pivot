from abc import ABC, abstractmethod

from src.pipeline.context import PipelineContext


class PipelineStep(ABC):
    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError
