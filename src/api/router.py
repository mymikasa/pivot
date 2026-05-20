from fastapi import APIRouter

from src.api.chat import router as chat_router
from src.api.parse_task import router as parse_task_router
from src.api.search import router as search_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(parse_task_router)
api_router.include_router(search_router)
api_router.include_router(chat_router)
