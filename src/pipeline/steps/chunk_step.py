import re

from llama_index.core.schema import TextNode

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class ChunkStep(PipelineStep):
    def __init__(self, chunk_token_num: int = 512, overlap: int = 50) -> None:
        if chunk_token_num <= 0:
            raise ValueError("chunk_token_num 必须大于 0")
        if overlap < 0 or overlap >= chunk_token_num:
            raise ValueError("overlap 必须大于等于 0 且小于 chunk_token_num")
        self.chunk_token_num = chunk_token_num
        self.overlap = overlap

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        result: list[TextNode] = []
        step_size = self.chunk_token_num - self.overlap
        ctx.metadata["chunk_size"] = self.chunk_token_num
        ctx.metadata["chunk_overlap"] = self.overlap

        for node in ctx.nodes:
            tokens = node.text.split()
            for start in range(0, len(tokens), step_size):
                window = tokens[start : start + self.chunk_token_num]
                if not window:
                    continue
                result.append(TextNode(
                    text=" ".join(window),
                    metadata={**node.metadata, "token_count": len(window)},
                ))

        ctx.nodes = result
        return ctx
