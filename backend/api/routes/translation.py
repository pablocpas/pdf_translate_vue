"""
Translation management endpoints.

This module handles translation task management and data operations,
extracted from the original monolithic main.py file.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any

from shared.models.translation import TranslationTask
from shared.models.exceptions import FileError, ValidationError
from shared.utils.logging_utils import get_logger
from api.dependencies import (
    get_file_service, 
    get_translation_service,
    get_task_service
)
from services.file_service import FileService
from services.translation_service import TranslationService
from services.task_service import TaskService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/translation/{task_id}/status", response_model=TranslationTask)
async def get_translation_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> TranslationTask:
    """
    Get the current status of a translation task.
    
    Args:
        task_id: Translation task identifier
        task_service: Task service dependency
        
    Returns:
        TranslationTask: Current task status
    """
    logger.info(f"Status request for task: {task_id}")
    return task_service.get_task_status(task_id)


@router.get("/translation/{task_id}/data", response_model=Dict[str, Any])
async def get_translation_data(
    task_id: str,
    file_service: FileService = Depends(get_file_service),
    translation_service: TranslationService = Depends(get_translation_service)
) -> Dict[str, Any]:
    """
    Get translation data for editing.
    
    This endpoint replaces the complex data transformation logic
    that was embedded in the original endpoint.
    
    Args:
        task_id: Translation task identifier
        file_service: File service dependency
        translation_service: Translation service dependency
        
    Returns:
        Dict[str, Any]: Formatted translation data for frontend
        
    Raises:
        HTTPException: If translation data is not found
    """
    logger.info(f"Translation data request for task: {task_id}")
    
    try:
        # Load raw translation data
        raw_data = file_service.load_translation_data(task_id)
        
        # Transform for frontend editing
        formatted_data = translation_service.transform_translation_data_for_editing(
            raw_data
        )
        
        return formatted_data
        
    except FileError as e:
        if e.code == "TRANSLATION_DATA_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=f"Translation data not found for task: {task_id}"
            )
        raise  # Re-raise other file errors


@router.put("/translation/{task_id}/data", response_model=Dict[str, str])
async def update_translation_data(
    task_id: str,
    translation_data: Dict[str, Any] = Body(..., description="Updated translation data"),
    file_service: FileService = Depends(get_file_service),
    translation_service: TranslationService = Depends(get_translation_service)
) -> Dict[str, str]:
    """
    Update translation data and regenerate PDF.
    
    This endpoint handles the complex workflow that was embedded
    in the original update endpoint.
    
    Args:
        task_id: Translation task identifier
        translation_data: Updated translation data from frontend
        file_service: File service dependency
        translation_service: Translation service dependency
        
    Returns:
        Dict[str, str]: Success message
        
    Raises:
        ValidationError: If data validation fails
    """
    logger.info(f"Translation data update for task: {task_id}")
    
    # Validate task ID
    from shared.utils.validation import validate_task_id
    validate_task_id(task_id)
    
    # Prepare data for regeneration
    processed_translation_data, position_data = (
        translation_service.prepare_translation_data_for_regeneration(
            translation_data
        )
    )
    
    # Save updated translation data
    file_service.save_translation_data(task_id, processed_translation_data)
    
    # Start PDF regeneration task
    translation_service.regenerate_pdf_task(
        task_id=task_id,
        translation_data=processed_translation_data,
        position_data=position_data
    )
    
    logger.info(f"Translation data updated and regeneration started: {task_id}")
    
    return {
        "message": "Translation data updated and PDF regeneration started",
        "task_id": task_id
    }


@router.delete("/translation/{task_id}", response_model=Dict[str, str])
async def cancel_translation(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, str]:
    """
    Cancel a running translation task.
    
    Args:
        task_id: Translation task identifier
        task_service: Task service dependency
        
    Returns:
        Dict[str, str]: Cancellation confirmation
    """
    logger.info(f"Cancel request for task: {task_id}")
    
    success = task_service.cancel_task(task_id)
    
    if success:
        return {
            "message": "Translation task cancelled successfully",
            "task_id": task_id
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel translation task"
        )