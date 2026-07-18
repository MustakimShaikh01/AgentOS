"""
FastAPI application entry point.

Structure:
    - Lifespan: startup/shutdown hooks for DB, Redis
    - CORS: configured for Next.js frontend
    - Routers: each module registers its own router
    - Error handlers: consistent error response format
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.agent.router import router as agent_router

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    log.info("AgentOS API starting", version=settings.version)
    # DB tables created via Alembic migrations (not here)
    # Redis connection is lazy (created on first request)
    yield
    log.info("AgentOS API shutting down")


app = FastAPI(
    title="AgentOS API",
    description="Enterprise Agent Operating System — API",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(agent_router, prefix="/api")


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
    }
