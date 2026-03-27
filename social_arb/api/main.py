"""FastAPI application factory."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from social_arb.api.deps import ensure_db, get_config, get_db_path
from social_arb.api.routes import (
    health, instruments, signals, reviews, analysis, mosaics, theses, positions, tasks, stepps, sentiment,
)
from social_arb.tasks.queue import TaskQueue
from social_arb.tasks.scheduler import TaskScheduler
from social_arb.tasks.workers import handle_collect, handle_analyze, handle_backfill, handle_train_stepps, handle_enrich_sentiment

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
    queue.register_handler("train_stepps", handle_train_stepps)
    queue.register_handler("enrich_sentiment", handle_enrich_sentiment)
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
    from social_arb.logging_config import setup_logging
    setup_logging()

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

    # Request logging
    from social_arb.api.middleware import RequestLoggingMiddleware, add_rate_limiting
    app.add_middleware(RequestLoggingMiddleware)
    add_rate_limiting(app)

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
    app.include_router(stepps.router)
    app.include_router(sentiment.router)

    @app.get("/")
    def root():
        return {"app": "Social Arb", "version": "2.0.0", "docs": "/docs"}

    # Serve static frontend (production mode)
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.isdir(static_dir):
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve SPA index.html for all non-API routes."""
            if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "redoc"):
                return {"error": "Not found"}
            # Try to serve static file first
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # Fall back to index.html for SPA routing
            index_path = os.path.join(static_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            return {"error": "Frontend not built. Run: ./build-frontend.sh"}

    return app


# For `uvicorn social_arb.api.main:app`
app = create_app()
