import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
import bootstrap
from app.routes.game_routes import router as game_router

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ransom Rampage API",
    version="0.1.0",
    description="Cyber-crisis simulation API"
)

# CORS middleware (allow all origins for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}

# Include routers
app.include_router(game_router, prefix="/api")

# Startup event
@app.on_event("startup")
async def startup_event():
    await bootstrap.startup()
    logger.info("Application startup completed")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await bootstrap.shutdown()
    logger.info("Application shutdown completed")
