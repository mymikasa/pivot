import re

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext, Section


class CleanStep(PipelineStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        seen: set[str] = set()
        cleaned_sections: list[Section] = []

        for section in ctx.sections:
            text = re.sub(r"\s+", " ", section.text).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned_sections.append(Section(text=text, metadata=section.metadata))

        ctx.sections = cleaned_sections
        return ctx
