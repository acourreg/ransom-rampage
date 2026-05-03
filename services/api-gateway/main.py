import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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

# Rate limiting (Redis-backed)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["30/minute"]
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics — auto-instruments all endpoints
# Exposes /metrics for Prometheus to scrape
Instrumentator().instrument(app).expose(app)

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
