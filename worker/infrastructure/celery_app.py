"""
Celery application configuration.

This module centralizes Celery configuration that was duplicated
across the original backend and worker code.
"""

from celery import Celery

from shared.config import get_settings
from shared.utils.logging_utils import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


def create_celery_app() -> Celery:
    """
    Create and configure Celery application.
    
    This factory pattern replaces the global Celery configuration
    and provides better testability.
    
    Returns:
        Celery: Configured Celery application
    """
    settings = get_settings()
    
    # Create Celery app
    app = Celery('pdf_translator')
    
    # Configure Celery
    app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=settings.task_timeout_seconds,
        task_soft_time_limit=settings.task_timeout_seconds - 60,  # 1 minute before hard limit
        worker_max_tasks_per_child=10,  # Restart workers after 10 tasks to prevent memory leaks
        worker_prefetch_multiplier=1,   # Process one task at a time for better resource management
    )
    
    logger.info("Celery application configured successfully")
    return app


# Create the global Celery app instance
celery_app = create_celery_app()