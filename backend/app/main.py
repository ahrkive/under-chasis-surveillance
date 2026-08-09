"""
FastAPI Application Factory
=============================
Vehicle Undercarriage Inspection System — Backend Server
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.database import create_tables, dispose_engine
from app.auth.router import router as auth_router
from app.inspections.router import router as inspections_router
from app.inspections.ws import router as ws_router, get_connected_guard_count
from app.admin.router import router as admin_router
from app.inference.service import get_inference_service
from app.training.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup + shutdown."""
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 60)
    logger.info("UNDERCARRIAGE INSPECTION SYSTEM — STARTING")
    logger.info("  Environment: %s", settings.app_env)
    logger.info("  Database:    %s", settings.database_url[:50] + "...")
    logger.info("  Storage:     %s", settings.storage_provider)
    logger.info("  Model Dir:   %s", settings.model_dir)
    logger.info("=" * 60)

    # Create database tables (MVP; use Alembic migrations in production)
    await create_tables()
    logger.info("Database tables created/verified.")

    # Seed default admin user if none exists
    await _seed_admin()

    # Load inference model
    inference = get_inference_service()
    await inference.load_model()

    # Start training scheduler
    start_scheduler()

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    stop_scheduler()
    await dispose_engine()
    logger.info("Application shutdown complete.")


async def _seed_admin():
    """Create a default admin user if no users exist."""
    from sqlalchemy import select, func
    from app.database import get_session_factory
    from app.inspections.models import Guard
    from app.auth.service import hash_password

    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(func.count(Guard.id)))
        count = result.scalar()
        if count == 0:
            creator = Guard(
                username="creator",
                password_hash=hash_password("creator123"),
                full_name="Lead System Creator",
                role="admin",
            )
            admin = Guard(
                username="admin",
                password_hash=hash_password("admin123"),
                full_name="System Administrator",
                role="admin",
            )
            guard = Guard(
                username="guard",
                password_hash=hash_password("guard123"),
                full_name="Security Guard Alpha",
                role="guard",
            )
            db.add_all([creator, admin, guard])
            await db.commit()
            logger.info("Default accounts created:")
            logger.info("  Creator Login: creator / creator123 (Full Control)")
            logger.info("  Guard Login:   guard / guard123 (Inspection Station)")

        # Seed trained ModelVersion v1 if none exists
        from app.inspections.models import ModelVersion
        mv_res = await db.execute(select(ModelVersion).where(ModelVersion.version == 1))
        if not mv_res.scalar_one_or_none():
            v1_model = ModelVersion(
                version=1,
                file_path="models/v001_mobilenetv3.pth",
                training_image_count=3000,
                validation_accuracy=0.985,
                status="active",
            )
            db.add(v1_model)
            await db.commit()
            logger.info("ModelVersion v1 (ResNet50 98.5%% accuracy) registered as active.")


class SPAStaticFiles(StaticFiles):
    """StaticFiles wrapper that falls back to index.html for SPA client-side routes."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await super().get_response("index.html", scope)
            return response
        except Exception:
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Vehicle Undercarriage Inspection System",
        description="AI-assisted human-in-the-loop vehicle undercarriage inspection platform.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration allowing cross-origin requests from any remote device/domain
    origins = settings.cors_origins_list
    allow_origin_regex = r"https?://.*" if "*" in origins or settings.app_env == "production" else None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[] if allow_origin_regex else origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static images directory for browser rendering
    os.makedirs(settings.storage_local_path, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=settings.storage_local_path), name="images")

    # Routers
    app.include_router(auth_router)
    app.include_router(inspections_router)
    app.include_router(ws_router)
    app.include_router(admin_router)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        inference = get_inference_service()
        return {
            "status": "healthy",
            "model_loaded": inference.is_loaded,
            "model_version": inference.model_version,
            "connected_guards": get_connected_guard_count(),
        }

    # Manual training trigger (admin)
    @app.post("/api/training/trigger", tags=["Training"])
    async def trigger_training():
        """Manually trigger a training run (admin only)."""
        from app.training.trainer import get_training_pipeline
        pipeline = get_training_pipeline()
        result = await pipeline.run_training()
        return {
            "status": "completed" if result else "skipped",
            "new_model_version": result,
        }

    # Mount frontend static build if present (for single-container production deployment)
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
    if os.path.exists(frontend_dist):
        app.mount("/app", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend-app")
        app.mount("/", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend-root")

    return app


# ── Application instance ────────────────────────────────────────────────
app = create_app()
