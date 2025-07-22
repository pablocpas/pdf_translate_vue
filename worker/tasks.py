"""
Celery task definitions.

This module defines the Celery tasks for PDF processing, significantly
simplified from the original monolithic implementation.
"""

from typing import Dict, Any

from shared.models.task import TaskResult
from shared.utils.logging_utils import get_logger
from infrastructure.celery_app import celery_app
from core.orchestrator import TranslationOrchestrator

logger = get_logger(__name__)


@celery_app.task(name='process_pdf', bind=True)
def process_pdf(
    self, 
    pdf_path: str, 
    target_language: str, 
    task_id: str, 
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Process a PDF file for translation.
    
    This task orchestrates the complete translation workflow,
    replacing the complex logic in the original task function.
    
    Args:
        self: Celery task instance (for progress updates)
        pdf_path: Path to the PDF file
        target_language: Target language code
        task_id: Unique task identifier
        model: Translation model to use
        
    Returns:
        Dict[str, Any]: Task result
    """
    logger.info(f"Starting PDF processing: {pdf_path} -> {target_language}")
    
    # Create orchestrator with progress callback
    def update_progress(current: int, total: int, status: str = "processing"):
        """Update task progress."""
        progress = {
            'current': current,
            'total': total,
            'percent': int((current / total) * 100) if total > 0 else 0,
            'status': status
        }
        self.update_state(state='PROGRESS', meta={'progress': progress})
    
    orchestrator = TranslationOrchestrator(
        task_id=task_id,
        progress_callback=update_progress
    )
    
    try:
        # Execute translation workflow
        result = orchestrator.process_translation(
            pdf_path=pdf_path,
            target_language=target_language,
            model=model
        )
        
        if result.success:
            logger.info(f"PDF processing completed successfully: {task_id}")
            return {
                "success": True,
                "translated_file": result.data.get("output_path"),
                "task_id": task_id
            }
        else:
            logger.error(f"PDF processing failed: {result.error.message}")
            return {
                "error": result.error.message,
                "error_code": result.error.code,
                "task_id": task_id
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in PDF processing: {str(e)}", exc_info=True)
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
            "task_id": task_id
        }


@celery_app.task(name='regenerate_pdf', bind=True)
def regenerate_pdf(
    self,
    task_id: str, 
    translation_data: Dict[str, Any], 
    position_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Regenerate PDF with updated translations.
    
    This task handles PDF regeneration with user-edited translations,
    replacing the complex regeneration logic in the original task.
    
    Args:
        self: Celery task instance (for progress updates)
        task_id: Task identifier
        translation_data: Updated translation data
        position_data: Position data for text blocks
        
    Returns:
        Dict[str, Any]: Task result
    """
    logger.info(f"Starting PDF regeneration: {task_id}")
    
    # Create orchestrator with progress callback
    def update_progress(current: int, total: int, status: str = "regenerating"):
        """Update task progress."""
        progress = {
            'current': current,
            'total': total,
            'percent': int((current / total) * 100) if total > 0 else 0,
            'status': status
        }
        self.update_state(state='PROGRESS', meta={'progress': progress})
    
    orchestrator = TranslationOrchestrator(
        task_id=task_id,
        progress_callback=update_progress
    )
    
    try:
        # Execute regeneration workflow
        result = orchestrator.regenerate_pdf(
            translation_data=translation_data,
            position_data=position_data
        )
        
        if result.success:
            logger.info(f"PDF regeneration completed successfully: {task_id}")
            return {
                "success": True,
                "output_path": result.data.get("output_path"),
                "task_id": task_id
            }
        else:
            logger.error(f"PDF regeneration failed: {result.error.message}")
            return {
                "error": result.error.message,
                "error_code": result.error.code,
                "task_id": task_id
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in PDF regeneration: {str(e)}", exc_info=True)
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
            "task_id": task_id
        }