"""
Font management service.

This module handles font loading and language-specific font selection,
replacing the scattered font logic in the original processor.py.
"""

import os
from pathlib import Path
from typing import Dict, Any

from shared.models.task import TaskResult
from shared.models.exceptions import FontError
from shared.utils.logging_utils import get_logger
from shared.config.constants import FONT_MAPPING

from .registry import FontRegistry

logger = get_logger(__name__)


class FontManager:
    """
    Service for managing fonts and language-specific font selection.
    
    This class consolidates font management logic that was scattered
    throughout the original processor.py and layout.py files.
    """
    
    def __init__(self):
        """Initialize the font manager."""
        self.registry = FontRegistry()
        self._initialize_fonts()
    
    def _initialize_fonts(self):
        """Initialize and register all available fonts."""
        try:
            self.registry.register_all_fonts()
            logger.info("Font manager initialized successfully")
        except Exception as e:
            logger.error(f"Font manager initialization failed: {str(e)}")
    
    def prepare_font_for_language(self, target_language: str) -> TaskResult:
        """
        Prepare the appropriate font for a target language.
        
        This method replaces the font selection logic that was
        embedded in the original processing workflow.
        
        Args:
            target_language: Target language code
            
        Returns:
            TaskResult: Font preparation result
        """
        logger.debug(f"Preparing font for language: {target_language}")
        
        try:
            # Get font name for language
            font_name = self._get_font_for_language(target_language)
            
            # Verify font is available
            font_info = self.registry.get_font_info(font_name)
            if not font_info["available"]:
                return TaskResult.error_result(
                    error_code="FONT_NOT_AVAILABLE",
                    error_message=f"Font '{font_name}' not available for language '{target_language}'"
                )
            
            logger.debug(f"Font prepared: {font_name} for {target_language}")
            return TaskResult.success_result(
                data={
                    "font_name": font_name,
                    "font_path": font_info.get("path"),
                    "font_family": font_info.get("family"),
                    "target_language": target_language
                },
                metadata=font_info
            )
            
        except Exception as e:
            logger.error(f"Font preparation failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="FONT_PREPARATION_FAILED",
                error_message=f"Font preparation failed: {str(e)}"
            )
    
    def _get_font_for_language(self, language_code: str) -> str:
        """
        Get the appropriate font name for a language.
        
        Args:
            language_code: Language code
            
        Returns:
            str: Font name
        """
        # Normalize language code
        normalized_code = language_code.lower().strip()
        
        # Get font from mapping
        font_name = FONT_MAPPING.get(normalized_code, "OpenSans")
        
        logger.debug(f"Language '{normalized_code}' -> Font '{font_name}'")
        return font_name
    
    def get_available_fonts(self) -> TaskResult:
        """
        Get information about all available fonts.
        
        Returns:
            TaskResult: Available fonts information
        """
        try:
            fonts_info = self.registry.list_available_fonts()
            
            return TaskResult.success_result(
                data={"fonts": fonts_info},
                metadata={"total_fonts": len(fonts_info)}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="FONTS_LISTING_FAILED",
                error_message=f"Failed to list available fonts: {str(e)}"
            )
    
    def validate_font_for_text(
        self, 
        font_name: str, 
        text_sample: str
    ) -> TaskResult:
        """
        Validate if a font can properly render a text sample.
        
        This method can be used to check if a font supports
        the characters needed for a specific language.
        
        Args:
            font_name: Name of the font to validate
            text_sample: Text sample to test
            
        Returns:
            TaskResult: Validation result
        """
        try:
            font_info = self.registry.get_font_info(font_name)
            
            if not font_info["available"]:
                return TaskResult.error_result(
                    error_code="FONT_NOT_AVAILABLE",
                    error_message=f"Font '{font_name}' is not available"
                )
            
            # Basic character support check
            # In a production system, this would be more sophisticated
            supported_chars = self._get_supported_characters(font_name)
            unsupported_chars = []
            
            for char in set(text_sample):
                if char not in supported_chars and ord(char) > 127:
                    unsupported_chars.append(char)
            
            support_ratio = 1.0 - (len(unsupported_chars) / len(set(text_sample)))
            
            return TaskResult.success_result(
                data={
                    "font_name": font_name,
                    "support_ratio": support_ratio,
                    "fully_supported": len(unsupported_chars) == 0,
                    "unsupported_characters": unsupported_chars
                },
                metadata={
                    "text_length": len(text_sample),
                    "unique_characters": len(set(text_sample))
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="FONT_VALIDATION_FAILED",
                error_message=f"Font validation failed: {str(e)}"
            )
    
    def _get_supported_characters(self, font_name: str) -> set:
        """
        Get the set of characters supported by a font.
        
        This is a simplified implementation. In production,
        you would use font analysis libraries.
        
        Args:
            font_name: Font name
            
        Returns:
            set: Set of supported characters
        """
        # Basic ASCII characters are supported by all fonts
        basic_chars = set(chr(i) for i in range(32, 127))
        
        # Extended character sets for specific fonts
        extended_chars = {
            'OpenSans': set('áéíóúüñç'),
            'STSong-Light': set('中文'),
            'HeiseiMin-W3': set('ひらがなカタカナ漢字'),
            'HYSMyeongJo-Medium': set('한글')
        }
        
        return basic_chars.union(extended_chars.get(font_name, set()))
    
    def get_font_metrics(self, font_name: str, font_size: float = 12) -> TaskResult:
        """
        Get metrics for a font at a specific size.
        
        Args:
            font_name: Font name
            font_size: Font size in points
            
        Returns:
            TaskResult: Font metrics information
        """
        try:
            font_info = self.registry.get_font_info(font_name)
            
            if not font_info["available"]:
                return TaskResult.error_result(
                    error_code="FONT_NOT_AVAILABLE",
                    error_message=f"Font '{font_name}' is not available"
                )
            
            # Calculate basic metrics
            # In production, these would be calculated using font libraries
            metrics = {
                "font_name": font_name,
                "font_size": font_size,
                "line_height": font_size * 1.2,  # Typical line height
                "ascent": font_size * 0.8,       # Typical ascent
                "descent": font_size * 0.2,      # Typical descent
                "cap_height": font_size * 0.7,   # Typical cap height
                "x_height": font_size * 0.5      # Typical x-height
            }
            
            return TaskResult.success_result(
                data=metrics,
                metadata={"calculated": True, "approximate": True}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="FONT_METRICS_FAILED",
                error_message=f"Failed to get font metrics: {str(e)}"
            )
    
    def cleanup_fonts(self) -> TaskResult:
        """
        Clean up font resources.
        
        This method can be called during application shutdown
        to clean up any font-related resources.
        
        Returns:
            TaskResult: Cleanup result
        """
        try:
            self.registry.cleanup()
            logger.info("Font manager cleanup completed")
            
            return TaskResult.success_result(
                data={"status": "cleaned"},
                metadata={"message": "Font resources cleaned up successfully"}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="FONT_CLEANUP_FAILED",
                error_message=f"Font cleanup failed: {str(e)}"
            )