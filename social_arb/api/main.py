"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from social_arb.api.deps import ensure_db, get_config
from social_arb.api.routes import health, instruments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    ensure_db()
    yield


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

    @app.get("/")
    def root():
        return {"app": "Social Arb", "version": "2.0.0", "docs": "/docs"}

    return app


# For `uvicorn social_arb.api.main:app`
app = create_app()
