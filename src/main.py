# src/main.py

# import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from src.common.database.database import connect_to_db, close_db_connection
from src.common.config import settings
from src.common.rate_limit import limiter
from src.router.routers import include_routers

# Initialize listeners
import src.events.listeners.auth_listener
import src.events.listeners.achievement_listener
import src.events.listeners.notification_listener
# from src.common.utils.email import test_email

# Centralized logging configuration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    # Schedule test_email to run in the background within the existing event loop
    # asyncio.create_task(test_email())
    yield
    await close_db_connection()

# Initialize FastAPI app with lifespan manager
app = FastAPI(
    title="Retgrow Learn API",
    description="Retgrow Initiative's platform to aid students' tech learning journey.",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Middleware for CORS using allowed origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from a separate file
include_routers(app)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "API is running"}

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("src/templates/index.html")