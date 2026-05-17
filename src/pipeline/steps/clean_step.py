import re

from llama_index.core.schema import TextNode

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class CleanStep(PipelineStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        seen: set[str] = set()
        cleaned: list[TextNode] = []

        for node in ctx.nodes:
            text = re.sub(r"\s+", " ", node.text).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(TextNode(text=text, metadata=node.metadata))

        ctx.nodes = cleaned
        return ctx
