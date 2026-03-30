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
    health, instruments, signals, reviews, analysis, mosaics, theses, positions, tasks, stepps, sentiment, scheduler, lattice, alerts,
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

    # Initialize scheduler (skip with DISABLE_SCHEDULER=1 to keep app responsive)
    scheduler = TaskScheduler(queue=queue, db_path=db_path)
    if not os.environ.get("DISABLE_SCHEDULER"):
        await scheduler.start()
    else:
        logger.info("Scheduler disabled via DISABLE_SCHEDULER env var")

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
    app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
    app.include_router(lattice.router)
    app.include_router(stepps.router)
    app.include_router(sentiment.router)
    app.include_router(scheduler.router)

    # Serve static frontend (production mode)
    # Resolve static dir from multiple possible locations to handle
    # different __file__ resolution across environments (pip -e, direct run, etc.)
    _this_file = os.path.abspath(__file__)                         # .../social_arb/api/main.py
    _api_dir = os.path.dirname(_this_file)                         # .../social_arb/api/
    _pkg_dir = os.path.dirname(_api_dir)                           # .../social_arb/
    _project_dir = os.path.dirname(_pkg_dir)                       # .../Trader/

    # Try multiple candidate paths (including CWD-based for reliability)
    _cwd = os.getcwd()
    _candidates = [
        os.path.join(_pkg_dir, "static"),                          # social_arb/static/  (vite default)
        os.path.join(_api_dir, "static"),                          # social_arb/api/static/
        os.path.join(_project_dir, "social_arb", "static"),        # from project root
        os.path.join(_cwd, "social_arb", "static"),                # from CWD (most reliable)
        os.path.join(_cwd, "static"),                              # if CWD is social_arb/
    ]
    static_dir = None
    for _c in _candidates:
        if os.path.isdir(_c) and os.path.isfile(os.path.join(_c, "index.html")):
            static_dir = _c
            break

    logger.info(f"Static dir resolution: __file__={_this_file}, candidates={_candidates}, selected={static_dir}")

    if static_dir:
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve SPA index.html for all non-API routes."""
            if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "redoc"):
                return {"error": "Not found"}
            # Try to serve static file first
            if full_path:
                file_path = os.path.join(static_dir, full_path)
                if os.path.isfile(file_path):
                    return FileResponse(file_path)
            # Fall back to index.html for SPA routing (including root /)
            index_path = os.path.join(static_dir, "index.html")
            return FileResponse(
                index_path,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
    else:
        logger.warning(f"No static frontend found in any of: {_candidates}")

        @app.get("/")
        def root():
            return {"app": "Social Arb", "version": "2.0.0", "docs": "/docs"}

    return app


# For `uvicorn social_arb.api.main:app`
app = create_app()
