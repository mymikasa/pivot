import hashlib
import random

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class EmbedStep(PipelineStep):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        api_base: str = "https://api.openai.com/v1",
        dim: int = 1536,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.dim = dim

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        for node in ctx.nodes:
            node.embedding = await self.embed_text(node.text)
        return ctx

    async def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
            rng = random.Random(seed)
            return [rng.uniform(-1.0, 1.0) for _ in range(self.dim)]
        raise RuntimeError("远程 embedding 调用将在接入 OpenAI SDK 后启用")
