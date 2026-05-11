from fastapi import FastAPI

from src.routers import auth, users

app = FastAPI(title="Pivot", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
