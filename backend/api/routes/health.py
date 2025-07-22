"""
Health check endpoints.

This module provides application health monitoring endpoints.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from shared.config import get_settings
from shared.utils.logging_utils import get_logger
from api.dependencies import get_task_service
from services.task_service import TaskService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    settings = Depends(get_settings),
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    return {
        "status": "healthy",
        "service": "pdf-translator-backend",
        "version": "1.0.0"
    }


@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    settings = Depends(get_settings),
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Detailed health check including dependencies.
    
    Returns:
        Dict[str, Any]: Detailed health information
    """
    health_info = {
        "status": "healthy",
        "service": "pdf-translator-backend",
        "version": "1.0.0",
        "config": {
            "upload_folder": str(settings.upload_folder),
            "translated_folder": str(settings.translated_folder),
            "debug": settings.debug
        }
    }
    
    # Check Celery connection
    try:
        active_tasks = task_service.get_active_tasks()
        health_info["celery"] = {
            "status": "connected",
            "active_tasks_count": len(active_tasks.get("active", {})),
            "scheduled_tasks_count": len(active_tasks.get("scheduled", {}))
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {str(e)}")
        health_info["celery"] = {
            "status": "error",
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    return health_info