"""
Translation orchestration service.

This service coordinates translation tasks, replacing the complex logic
scattered throughout the original backend endpoints.
"""

import json
from typing import Dict, Any, Optional
from celery import Celery

from shared.config.base import Settings
from shared.models.translation import TranslationTask, TranslationData
from shared.models.exceptions import ValidationError, ProcessingError
from shared.utils.logging_utils import get_logger
from shared.utils.validation import validate_language_code, validate_task_id

logger = get_logger(__name__)


class TranslationService:
    """
    Service for coordinating translation operations.
    
    This consolidates translation workflow logic that was mixed
    with API endpoint logic in the original code.
    """
    
    def __init__(self, settings: Settings, celery_app: Celery):
        """
        Initialize the translation service.
        
        Args:
            settings: Application settings
            celery_app: Celery application instance
        """
        self.settings = settings
        self.celery_app = celery_app
    
    def start_translation_task(
        self,
        task_id: str,
        file_path: str,
        target_language: str,
        model: str = "gpt-4o-mini"
    ) -> TranslationTask:
        """
        Start a new translation task.
        
        Args:
            task_id: Unique task identifier
            file_path: Path to the uploaded PDF file
            target_language: Target language code
            model: Translation model to use
            
        Returns:
            TranslationTask: Created translation task
            
        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate inputs
        validate_task_id(task_id)
        validate_language_code(target_language)
        
        # Create Celery task
        try:
            celery_task = self.celery_app.send_task(
                'process_pdf',
                args=[file_path, target_language, task_id, model],
                task_id=task_id
            )
            
            logger.info(f"Translation task started: {task_id}")
            
            return TranslationTask(
                id=task_id,
                status="pending",
                original_file=file_path,
                target_language=target_language,
                model=model
            )
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to start translation task: {str(e)}",
                code="TASK_START_FAILED",
                context={"task_id": task_id, "error": str(e)}
            )
    
    def regenerate_pdf_task(
        self,
        task_id: str,
        translation_data: Dict[str, Any],
        position_data: Dict[str, Any]
    ) -> None:
        """
        Start PDF regeneration task with updated translations.
        
        Args:
            task_id: Task identifier
            translation_data: Updated translation data
            position_data: Position data for text blocks
            
        Raises:
            ValidationError: If parameters are invalid
            ProcessingError: If task creation fails
        """
        validate_task_id(task_id)
        
        try:
            # Send regeneration task to Celery
            self.celery_app.send_task(
                'regenerate_pdf',
                args=[task_id, translation_data, position_data]
            )
            
            logger.info(f"PDF regeneration task started: {task_id}")
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to start PDF regeneration: {str(e)}",
                code="REGENERATION_START_FAILED",
                context={"task_id": task_id, "error": str(e)}
            )
    
    def transform_translation_data_for_editing(
        self, 
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform raw translation data for frontend editing.
        
        This method centralizes the complex data transformation logic
        that was embedded in the original API endpoint.
        
        Args:
            raw_data: Raw translation data from storage
            
        Returns:
            Dict[str, Any]: Transformed data for frontend
        """
        if not raw_data.get("pages"):
            return {"pages": [], "metadata": {}}
        
        transformed_pages = []
        
        for page_data in raw_data["pages"]:
            page_number = page_data.get("page_number", 1)
            translations = page_data.get("translations", [])
            
            # Transform each translation block
            transformed_translations = []
            for i, translation in enumerate(translations):
                transformed_translation = {
                    "id": f"page_{page_number}_block_{i}",
                    "original_text": translation.get("original_text", ""),
                    "translated_text": translation.get("translated_text", ""),
                    "position": {
                        "x": translation.get("x", 0),
                        "y": translation.get("y", 0),
                        "width": translation.get("width", 0),
                        "height": translation.get("height", 0)
                    },
                    "font_info": {
                        "size": translation.get("font_size", 12),
                        "family": translation.get("font_family", "OpenSans")
                    }
                }
                transformed_translations.append(transformed_translation)
            
            transformed_page = {
                "page_number": page_number,
                "translations": transformed_translations,
                "image_path": page_data.get("image_path", "")
            }
            transformed_pages.append(transformed_page)
        
        return {
            "pages": transformed_pages,
            "metadata": {
                "total_pages": len(transformed_pages),
                "source_language": raw_data.get("source_language", "auto"),
                "target_language": raw_data.get("target_language", "en"),
                "model": raw_data.get("model", "gpt-4o-mini")
            }
        }
    
    def prepare_translation_data_for_regeneration(
        self,
        frontend_data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Prepare translation data received from frontend for PDF regeneration.
        
        Args:
            frontend_data: Data from frontend editing interface
            
        Returns:
            tuple: (translation_data, position_data) for regeneration
        """
        translation_data = {"pages": []}
        position_data = {"pages": []}
        
        for page in frontend_data.get("pages", []):
            page_number = page.get("page_number", 1)
            
            # Prepare translation data
            page_translations = []
            page_positions = []
            
            for translation in page.get("translations", []):
                # Translation data
                translation_item = {
                    "original_text": translation.get("original_text", ""),
                    "translated_text": translation.get("translated_text", ""),
                    "target_language": frontend_data.get("metadata", {}).get("target_language", "en")
                }
                page_translations.append(translation_item)
                
                # Position data
                position = translation.get("position", {})
                font_info = translation.get("font_info", {})
                
                position_item = {
                    "x": position.get("x", 0),
                    "y": position.get("y", 0),
                    "width": position.get("width", 0),
                    "height": position.get("height", 0),
                    "font_size": font_info.get("size", 12),
                    "font_family": font_info.get("family", "OpenSans")
                }
                page_positions.append(position_item)
            
            translation_data["pages"].append({
                "page_number": page_number,
                "translations": page_translations
            })
            
            position_data["pages"].append({
                "page_number": page_number,
                "positions": page_positions
            })
        
        return translation_data, position_data