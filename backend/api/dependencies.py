"""
FastAPI dependency injection.

This module provides dependency injection for the API endpoints,
replacing direct instantiation scattered throughout the original code.
"""

from fastapi import Depends
from celery import Celery

from shared.config import get_settings
from services.file_service import FileService
from services.translation_service import TranslationService
from services.task_service import TaskService


def get_celery_app() -> Celery:
    """
    Get Celery application instance.
    
    Returns:
        Celery: Configured Celery application
    """
    settings = get_settings()
    
    return Celery(
        'pdf_translator',
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend
    )


def get_file_service(settings = Depends(get_settings)) -> FileService:
    """
    Get FileService instance.
    
    Args:
        settings: Application settings
        
    Returns:
        FileService: File service instance
    """
    return FileService(settings)


def get_translation_service(
    settings = Depends(get_settings),
    celery_app: Celery = Depends(get_celery_app)
) -> TranslationService:
    """
    Get TranslationService instance.
    
    Args:
        settings: Application settings
        celery_app: Celery application
        
    Returns:
        TranslationService: Translation service instance
    """
    return TranslationService(settings, celery_app)


def get_task_service(
    celery_app: Celery = Depends(get_celery_app)
) -> TaskService:
    """
    Get TaskService instance.
    
    Args:
        celery_app: Celery application
        
    Returns:
        TaskService: Task service instance
    """
    return TaskService(celery_app)