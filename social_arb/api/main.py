"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from social_arb.api.deps import ensure_db, get_config, get_db_path
from social_arb.api.routes import (
    health, instruments, signals, reviews, analysis, mosaics, theses, positions, tasks,
)
from social_arb.tasks.queue import TaskQueue
from social_arb.tasks.scheduler import TaskScheduler
from social_arb.tasks.workers import handle_collect, handle_analyze, handle_backfill

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start task queue and scheduler. Shutdown: stop them."""
    ensure_db()

    # Initialize task queue
    db_path = get_db_path()
    queue = TaskQueue(db_path=db_path)
    queue.register_handler("collect", handle_collect)
    queue.register_handler("analyze", handle_analyze)
    queue.register_handler("backfill", handle_backfill)
    await queue.start()

    # Initialize scheduler
    scheduler = TaskScheduler(queue=queue, db_path=db_path)
    await scheduler.start()

    # Store in app state
    app.state.queue = queue
    app.state.scheduler = scheduler

    logger.info("TaskQueue and TaskScheduler started")

    yield

    # Shutdown
    logger.info("Shutting down")
    await scheduler.stop()
    await queue.stop()
    logger.info("TaskQueue and TaskScheduler stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = get_config()

    app = FastAPI(
        title="Social Arb API",
        description="Information Arbitrage Platform — Camillo Cognitive Architecture",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(instruments.router, prefix="/api/v1", tags=["instruments"])
    app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
    app.include_router(mosaics.router, prefix="/api/v1", tags=["mosaics"])
    app.include_router(theses.router, prefix="/api/v1", tags=["theses"])
    app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
    app.include_router(positions.router, prefix="/api/v1", tags=["positions"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])

    @app.get("/")
    def root():
        return {"app": "Social Arb", "version": "2.0.0", "docs": "/docs"}

    return app


# For `uvicorn social_arb.api.main:app`
app = create_app()
