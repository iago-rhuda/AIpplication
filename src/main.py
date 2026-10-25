"""Main FastAPI application entrypoint with static file serving and lifecycle management."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes_applications import router as applications_router
from src.api.routes_cold_outreach import router as cold_outreach_router
from src.api.routes_doubts import router as doubts_router
from src.api.routes_jobs import router as jobs_router
from src.api.websocket_logs import router as ws_router
from src.config import settings
from src.database.session import init_db
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context initializing the database on startup."""
    logger.info("Initializing Stage AI Application Ecosystem...")
    await init_db()
    logger.info("Startup complete. System ready to process applications.")
    yield
    logger.info("Shutting down application cleanly.")


app = FastAPI(
    title="Stage AI Application Ecosystem",
    description="Autonomous prospecting, LaTeX resume generation, and Kanban tracking for UTC TN10.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware (allows seamless local browser access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API & WebSocket routers
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(doubts_router)
app.include_router(cold_outreach_router)
app.include_router(ws_router)

# Mount generated documents directory for viewing/downloading CVs and dossiers
output_dir = settings.OUTPUT_DIR
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# Mount local web dashboard
web_dir = settings.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.ENV == "development"),
    )
