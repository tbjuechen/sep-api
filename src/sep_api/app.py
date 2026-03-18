"""
FastAPI 应用工厂
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from .deps import _sessions
from .routers import auth, courses, user, xkcts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting SEP API Server...")
    yield
    logger.info("Shutting down SEP API Server...")
    for client in _sessions.values():
        await client.close()


app = FastAPI(
    title="国科大教务系统 API",
    description="国科大教务系统 API 中转站",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(user.router)
app.include_router(xkcts.router)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Welcome to SEP API", "docs": "/docs"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}
