"""
File upload endpoints.

This module handles PDF file uploads, extracted from the original
monolithic main.py file.
"""

import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends
from typing import Dict, Any

from shared.models.translation import TranslationTask
from shared.models.exceptions import ValidationError
from shared.utils.logging_utils import get_logger
from api.dependencies import get_file_service, get_translation_service
from services.file_service import FileService
from services.translation_service import TranslationService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=TranslationTask)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to translate"),
    target_language: str = Form(..., description="Target language code"),
    model: str = Form(default="gpt-4o-mini", description="Translation model"),
    file_service: FileService = Depends(get_file_service),
    translation_service: TranslationService = Depends(get_translation_service)
) -> TranslationTask:
    """
    Upload a PDF file and start translation process.
    
    This endpoint replaces the complex upload logic that was embedded
    in the original monolithic endpoint.
    
    Args:
        file: PDF file to upload
        target_language: Target language for translation
        model: Translation model to use
        file_service: File service dependency
        translation_service: Translation service dependency
        
    Returns:
        TranslationTask: Created translation task
        
    Raises:
        ValidationError: If file or parameters are invalid
    """
    logger.info(f"Upload request: {file.filename} -> {target_language}")
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_path = await file_service.save_uploaded_file(file, task_id)
    logger.info(f"File saved: {file_path}")
    
    # Start translation task
    translation_task = translation_service.start_translation_task(
        task_id=task_id,
        file_path=str(file_path),
        target_language=target_language,
        model=model
    )
    
    logger.info(f"Translation task created: {task_id}")
    return translation_task


@router.post("/upload/validate", response_model=Dict[str, Any])
async def validate_upload(
    file: UploadFile = File(..., description="File to validate"),
    file_service: FileService = Depends(get_file_service)
) -> Dict[str, Any]:
    """
    Validate a file before upload without saving it.
    
    Args:
        file: File to validate
        file_service: File service dependency
        
    Returns:
        Dict[str, Any]: Validation result
    """
    try:
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        # Reset file pointer for potential future reads
        await file.seek(0)
        
        # Validate file type
        if not file_service.is_valid_pdf(file.filename):
            return {
                "valid": False,
                "error": "Invalid file type. Only PDF files are supported.",
                "error_code": "INVALID_FILE_TYPE"
            }
        
        # Validate file size
        from shared.utils.file_utils import validate_file_size
        validate_file_size(file_size)
        
        return {
            "valid": True,
            "file_info": {
                "name": file.filename,
                "size": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
        }
        
    except ValidationError as e:
        return {
            "valid": False,
            "error": str(e),
            "error_code": e.code
        }
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "valid": False,
            "error": "Validation failed due to an unexpected error",
            "error_code": "VALIDATION_ERROR"
        }