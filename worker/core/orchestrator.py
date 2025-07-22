"""
Translation workflow orchestrator.

This module coordinates the complete translation workflow, replacing
the monolithic process_pdf function in the original processor.py.
"""

import json
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from shared.config import get_settings
from shared.models.task import TaskResult
from shared.models.exceptions import ProcessingError, FileError
from shared.utils.logging_utils import get_logger
from shared.utils.file_utils import ensure_directory_exists

from .document.analyzer import DocumentAnalyzer
from .document.extractor import TextExtractor  
from .document.reconstructor import PDFReconstructor
from .translation.translator import TranslationEngine
from .fonts.manager import FontManager

logger = get_logger(__name__)


class TranslationOrchestrator:
    """
    Orchestrates the complete PDF translation workflow.
    
    This class replaces the monolithic process_pdf function and provides
    a clean, testable interface for the translation process.
    """
    
    def __init__(
        self, 
        task_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            task_id: Unique task identifier
            progress_callback: Optional callback for progress updates
        """
        self.task_id = task_id
        self.settings = get_settings()
        self.progress_callback = progress_callback or self._default_progress_callback
        
        # Ensure required directories exist
        ensure_directory_exists(self.settings.translated_folder)
        ensure_directory_exists(self.settings.temp_folder)
        
        # Initialize components
        self.analyzer = DocumentAnalyzer()
        self.extractor = TextExtractor()
        self.translator = TranslationEngine()
        self.reconstructor = PDFReconstructor()
        self.font_manager = FontManager()
    
    def _default_progress_callback(self, current: int, total: int, status: str = "processing"):
        """Default progress callback that does nothing."""
        pass
    
    def _update_progress(self, step: int, total_steps: int, status: str = "processing"):
        """Update progress with error handling."""
        try:
            self.progress_callback(step, total_steps, status)
        except Exception as e:
            logger.warning(f"Progress callback failed: {str(e)}")
    
    def process_translation(
        self,
        pdf_path: str,
        target_language: str,
        model: str = "gpt-4o-mini"
    ) -> TaskResult:
        """
        Process a PDF file for translation.
        
        This method orchestrates the complete translation workflow:
        1. Document analysis and layout detection
        2. Text extraction with position information
        3. Translation of extracted text
        4. PDF reconstruction with translated content
        
        Args:
            pdf_path: Path to the input PDF file
            target_language: Target language code
            model: Translation model to use
            
        Returns:
            TaskResult: Processing result with output path or error
        """
        logger.info(f"Starting translation processing: {self.task_id}")
        
        try:
            # Step 1: Analyze document structure
            self._update_progress(1, 6, "analyzing document")
            analysis_result = self.analyzer.analyze_document(pdf_path)
            if not analysis_result.success:
                return analysis_result
            
            pages_data = analysis_result.data["pages"]
            logger.info(f"Document analyzed: {len(pages_data)} pages")
            
            # Step 2: Extract text from all pages
            self._update_progress(2, 6, "extracting text")
            extraction_result = self.extractor.extract_text_from_pages(pages_data)
            if not extraction_result.success:
                return extraction_result
                
            text_blocks = extraction_result.data["text_blocks"]
            logger.info(f"Text extracted: {len(text_blocks)} blocks")
            
            # Step 3: Translate text blocks
            self._update_progress(3, 6, "translating text")
            translation_result = self.translator.translate_text_blocks(
                text_blocks=text_blocks,
                target_language=target_language,
                model=model
            )
            if not translation_result.success:
                return translation_result
                
            translated_blocks = translation_result.data["translated_blocks"]
            logger.info(f"Text translated: {len(translated_blocks)} blocks")
            
            # Step 4: Prepare font for target language
            self._update_progress(4, 6, "preparing fonts")
            font_result = self.font_manager.prepare_font_for_language(target_language)
            if not font_result.success:
                return font_result
            
            # Step 5: Generate translated PDF
            self._update_progress(5, 6, "generating PDF")
            output_path = self._get_output_path(self.task_id)
            reconstruction_result = self.reconstructor.reconstruct_pdf(
                pages_data=pages_data,
                translated_blocks=translated_blocks,
                output_path=output_path,
                target_language=target_language
            )
            if not reconstruction_result.success:
                return reconstruction_result
            
            # Step 6: Save translation data for potential editing
            self._update_progress(6, 6, "saving data")
            data_save_result = self._save_translation_data(
                pages_data=pages_data,
                translated_blocks=translated_blocks,
                target_language=target_language,
                model=model
            )
            if not data_save_result.success:
                return data_save_result
            
            logger.info(f"Translation completed successfully: {output_path}")
            return TaskResult.success_result(
                data={"output_path": str(output_path)},
                metadata={
                    "pages_processed": len(pages_data),
                    "text_blocks": len(text_blocks),
                    "target_language": target_language,
                    "model": model
                }
            )
            
        except Exception as e:
            logger.error(f"Translation processing failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="TRANSLATION_PROCESSING_FAILED",
                error_message=f"Translation processing failed: {str(e)}",
                traceback=str(e)
            )
    
    def regenerate_pdf(
        self,
        translation_data: Dict[str, Any],
        position_data: Dict[str, Any]
    ) -> TaskResult:
        """
        Regenerate PDF with updated translations.
        
        Args:
            translation_data: Updated translation data
            position_data: Position data for text placement
            
        Returns:
            TaskResult: Regeneration result
        """
        logger.info(f"Starting PDF regeneration: {self.task_id}")
        
        try:
            # Step 1: Load existing translation data for context
            self._update_progress(1, 4, "loading data")
            existing_data = self._load_existing_translation_data()
            if not existing_data:
                return TaskResult.error_result(
                    error_code="EXISTING_DATA_NOT_FOUND",
                    error_message="Existing translation data not found"
                )
            
            # Extract target language
            target_language = self._extract_target_language(translation_data)
            
            # Step 2: Prepare fonts
            self._update_progress(2, 4, "preparing fonts")
            font_result = self.font_manager.prepare_font_for_language(target_language)
            if not font_result.success:
                return font_result
            
            # Step 3: Regenerate PDF with updated translations
            self._update_progress(3, 4, "regenerating PDF")
            output_path = self._get_output_path(self.task_id)
            regeneration_result = self.reconstructor.regenerate_pdf_with_updates(
                translation_data=translation_data,
                position_data=position_data,
                output_path=output_path,
                target_language=target_language
            )
            if not regeneration_result.success:
                return regeneration_result
            
            # Step 4: Update stored translation data
            self._update_progress(4, 4, "updating data")
            self._save_translation_data_dict(translation_data)
            
            logger.info(f"PDF regeneration completed: {output_path}")
            return TaskResult.success_result(
                data={"output_path": str(output_path)},
                metadata={"target_language": target_language}
            )
            
        except Exception as e:
            logger.error(f"PDF regeneration failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="PDF_REGENERATION_FAILED",
                error_message=f"PDF regeneration failed: {str(e)}",
                traceback=str(e)
            )
    
    def _get_output_path(self, task_id: str) -> Path:
        """Get the output path for translated PDF."""
        filename = f"{task_id}_translated.pdf"
        return self.settings.translated_folder / filename
    
    def _get_translation_data_path(self, task_id: str) -> Path:
        """Get the path for translation data JSON."""
        filename = f"{task_id}_translation_data.json"
        return self.settings.translated_folder / filename
    
    def _save_translation_data(
        self,
        pages_data: list,
        translated_blocks: list,
        target_language: str,
        model: str
    ) -> TaskResult:
        """Save translation data for potential editing."""
        try:
            # Build translation data structure
            translation_data = {
                "task_id": self.task_id,
                "target_language": target_language,
                "model": model,
                "pages": []
            }
            
            # Group translated blocks by page
            blocks_by_page = {}
            for block in translated_blocks:
                page_num = block.get("page_number", 1)
                if page_num not in blocks_by_page:
                    blocks_by_page[page_num] = []
                blocks_by_page[page_num].append(block)
            
            # Build page data
            for page_data in pages_data:
                page_num = page_data.get("page_number", 1)
                page_blocks = blocks_by_page.get(page_num, [])
                
                page_info = {
                    "page_number": page_num,
                    "image_path": page_data.get("image_path", ""),
                    "translations": [
                        {
                            "original_text": block.get("original_text", ""),
                            "translated_text": block.get("translated_text", ""),
                            "x": block.get("x", 0),
                            "y": block.get("y", 0),
                            "width": block.get("width", 0),
                            "height": block.get("height", 0),
                            "font_size": block.get("font_size", 12),
                            "target_language": target_language
                        }
                        for block in page_blocks
                    ]
                }
                translation_data["pages"].append(page_info)
            
            # Save to file
            data_path = self._get_translation_data_path(self.task_id)
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(translation_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Translation data saved: {data_path}")
            return TaskResult.success_result()
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="TRANSLATION_DATA_SAVE_FAILED",
                error_message=f"Failed to save translation data: {str(e)}"
            )
    
    def _save_translation_data_dict(self, translation_data: Dict[str, Any]) -> None:
        """Save translation data dictionary directly."""
        data_path = self._get_translation_data_path(self.task_id)
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, ensure_ascii=False, indent=2)
    
    def _load_existing_translation_data(self) -> Optional[Dict[str, Any]]:
        """Load existing translation data if available."""
        data_path = self._get_translation_data_path(self.task_id)
        if not data_path.exists():
            return None
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing translation data: {str(e)}")
            return None
    
    def _extract_target_language(self, translation_data: Dict[str, Any]) -> str:
        """Extract target language from translation data."""
        # Try to get from metadata first
        metadata = translation_data.get("metadata", {})
        if metadata.get("target_language"):
            return metadata["target_language"]
        
        # Try to get from first page/translation
        pages = translation_data.get("pages", [])
        if pages:
            first_page = pages[0]
            translations = first_page.get("translations", [])
            if translations:
                return translations[0].get("target_language", "en")
        
        return "en"  # Default fallback