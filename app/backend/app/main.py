from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging

from app.core.config import settings
from app.core.database import init_db, engine
from app.api.v1 import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Micro Drama SaaS...")
    await init_db()
    logger.info("Database initialized")
    # Resume auto-generate jobs left RUNNING by a restart — in the
    # background, never blocking startup; no-op when nothing is stale.
    try:
        from app.api.v1.auto_generate import resume_stale_jobs
        asyncio.create_task(resume_stale_jobs(engine))
    except Exception as exc:
        logger.warning(f"Could not schedule stale-job resume: {exc}")
    # Sama untuk VideoJob yang ditinggal pending/processing (P2-4 ronde 2).
    try:
        from app.api.v1.video import resume_stale_video_jobs
        asyncio.create_task(resume_stale_video_jobs(engine))
    except Exception as exc:
        logger.warning(f"Could not schedule stale video-job resume: {exc}")
    yield
    # Shutdown
    logger.info("Shutting down Micro Drama SaaS...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Micro Drama Production SaaS Platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)