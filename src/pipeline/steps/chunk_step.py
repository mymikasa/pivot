from src.pipeline.base import PipelineStep
from src.pipeline.context import Chunk, PipelineContext


class ChunkStep(PipelineStep):
    def __init__(self, chunk_token_num: int = 512, overlap: int = 50) -> None:
        if chunk_token_num <= 0:
            raise ValueError("chunk_token_num 必须大于 0")
        if overlap < 0 or overlap >= chunk_token_num:
            raise ValueError("overlap 必须大于等于 0 且小于 chunk_token_num")
        self.chunk_token_num = chunk_token_num
        self.overlap = overlap

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        chunks: list[Chunk] = []
        step_size = self.chunk_token_num - self.overlap

        for section in ctx.sections:
            tokens = section.text.split()
            for start in range(0, len(tokens), step_size):
                window = tokens[start : start + self.chunk_token_num]
                if not window:
                    continue
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        content=" ".join(window),
                        token_count=len(window),
                        metadata=section.metadata,
                    )
                )

        ctx.chunks = chunks
        return ctx
