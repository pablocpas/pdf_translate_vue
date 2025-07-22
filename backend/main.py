"""
FastAPI application entry point.

This is the main entry point for the backend API service, significantly
simplified from the original monolithic file.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings, ensure_required_directories
from shared.utils.logging_utils import configure_logging, get_logger

from api.routes import health, upload, translation, download
from api.middleware.error_handler import add_exception_handlers


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This factory pattern replaces the global app instance and makes
    the application more testable and configurable.
    
    Returns:
        FastAPI: Configured application instance
    """
    # Load settings and configure logging
    settings = get_settings()
    configure_logging()
    logger = get_logger(__name__)
    
    # Ensure required directories exist
    ensure_required_directories()
    logger.info(f"Upload directory: {settings.upload_folder}")
    logger.info(f"Translated directory: {settings.translated_folder}")
    
    # Create FastAPI app
    app = FastAPI(
        title="PDF Translator API",
        description="API for translating PDF documents while preserving layout",
        version="1.0.0",
        debug=settings.debug
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(translation.router, prefix="/api", tags=["translation"])
    app.include_router(download.router, prefix="/api", tags=["download"])
    
    logger.info("FastAPI application created successfully")
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )