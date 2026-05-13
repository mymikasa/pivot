import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core.config import settings
from src.core.database import SessionLocal
from src.core.minio import create_minio_client
from src.worker.task_runner import ParseTaskWorker

logging.basicConfig(level=settings.log_level)

minio = create_minio_client()
worker = ParseTaskWorker(SessionLocal, minio_client=minio)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.worker_enabled:
        worker.start()
    yield
    worker.stop()


app = FastAPI(
    title="Pivot",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
