"""
File download endpoints.

This module handles file download operations, extracted from the
original monolithic main.py file.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any

from shared.utils.logging_utils import get_logger
from api.dependencies import get_file_service
from services.file_service import FileService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/download/{task_id}")
async def download_translated_pdf(
    task_id: str,
    file_service: FileService = Depends(get_file_service)
) -> FileResponse:
    """
    Download the translated PDF file.
    
    Args:
        task_id: Translation task identifier
        file_service: File service dependency
        
    Returns:
        FileResponse: Translated PDF file
        
    Raises:
        HTTPException: If file is not found
    """
    logger.info(f"Download request for task: {task_id}")
    
    # Get translated file path
    file_path = file_service.get_translated_file_path(task_id)
    
    # Check if file exists
    if not file_service.file_exists(file_path):
        logger.warning(f"Translated file not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Translated file not found for task: {task_id}"
        )
    
    # Get file info for logging
    file_info = file_service.get_file_info(file_path)
    logger.info(f"Serving file: {file_path} (size: {file_info['size']} bytes)")
    
    # Return file response
    return FileResponse(
        path=str(file_path),
        filename=f"{task_id}_translated.pdf",
        media_type="application/pdf"
    )


@router.get("/download/{task_id}/info", response_model=Dict[str, Any])
async def get_download_info(
    task_id: str,
    file_service: FileService = Depends(get_file_service)
) -> Dict[str, Any]:
    """
    Get information about the translated file without downloading it.
    
    Args:
        task_id: Translation task identifier
        file_service: File service dependency
        
    Returns:
        Dict[str, Any]: File information
    """
    logger.info(f"Download info request for task: {task_id}")
    
    file_path = file_service.get_translated_file_path(task_id)
    file_info = file_service.get_file_info(file_path)
    
    if not file_info["exists"]:
        return {
            "available": False,
            "message": "Translated file not yet available"
        }
    
    return {
        "available": True,
        "file_info": {
            "name": file_info["name"],
            "size": file_info["size"],
            "size_mb": round(file_info["size"] / (1024 * 1024), 2),
            "modified": file_info["modified"]
        },
        "download_url": f"/api/download/{task_id}"
    }