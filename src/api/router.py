from fastapi import APIRouter

from src.api.parse_task import router as parse_task_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(parse_task_router)
