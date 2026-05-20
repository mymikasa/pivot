from sqlalchemy.orm import Session

from src.infrastructure.config import settings
from src.pipeline.executor import PipelineExecutor
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.parser_step import ParserStep
from src.pipeline.steps.store_step import StoreStep


def build_default_pipeline(db: Session) -> PipelineExecutor:
    return PipelineExecutor(
        [
            ParserStep(),
            CleanStep(),
            ChunkStep(chunk_token_num=512, overlap=50),
            EmbedStep(
                api_key=settings.embedding_api_key,
                model=settings.embedding_model,
                api_base=settings.embedding_api_base,
                dim=settings.embedding_dim,
            ),
            StoreStep(db),
        ]
    )
