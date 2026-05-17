import json
from html.parser import HTMLParser
from typing import Any

from llama_index.core.schema import TextNode

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


class ParserStep(PipelineStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        text = self._to_text(ctx.raw_binary, ctx.content_type)
        ctx.nodes = [
            TextNode(text=part.strip())
            for part in text.splitlines()
            if part.strip()
        ]
        return ctx

    def _to_text(self, raw_binary: bytes, content_type: str) -> str:
        if content_type == "application/json":
            data: Any = json.loads(raw_binary.decode("utf-8"))
            return json.dumps(data, ensure_ascii=False, indent=2)
        if content_type == "text/html":
            parser = _TextExtractor()
            parser.feed(raw_binary.decode("utf-8", errors="ignore"))
            return "\n".join(parser.parts)
        return raw_binary.decode("utf-8", errors="ignore")
