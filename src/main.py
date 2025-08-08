from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.error_handlers import setup_error_handlers
from src.logger import logger
from src.middleware import setup_middleware
from src.routes import auth, index, s3
from src.utils import get_current_date_time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    settings = get_settings()
    logger.info("🚀 Application starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    # Shutdown
    logger.info("🛑 Application shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="Web Service Template",
        description="A full-service Python web service template using FastAPI",
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # Set up middleware
    setup_middleware(app)

    # Set up error handlers
    setup_error_handlers(app)

    # Mount static files
    app.mount("/static", StaticFiles(directory="src/static"), name="static")

    # Include routers
    app.include_router(auth.router, prefix="/api")
    app.include_router(index.router, prefix="/web")
    app.include_router(s3.router)

    # Health check endpoints
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "timestamp": get_current_date_time(), "version": "0.1.0"}

    @app.get("/test", response_model=Dict[str, str])
    async def test() -> Dict[str, str]:
        """Test endpoint to verify the application is working."""
        return {
            "result": "success",
            "msg": f"It works! {get_current_date_time()}",
        }

    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, str]:
        """Root endpoint with basic application information."""
        return {"message": "Web Service Template API", "version": "0.1.0", "docs": "/docs", "health": "/health"}

    return app


# Create the application
app = create_app()
