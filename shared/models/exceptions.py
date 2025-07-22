"""
Custom exceptions for PDF Translator application.

This module defines all custom exceptions to provide better error handling
and replace the generic exception handling scattered throughout the codebase.
"""

from typing import Optional, Dict, Any


class PDFTranslatorError(Exception):
    """
    Base exception for all PDF Translator errors.
    
    This provides a common base for all application-specific exceptions
    and includes context information for better debugging.
    """
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None, 
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            context: Additional context information
        """
        super().__init__(message)
        self.code = code or self.__class__.__name__
        self.context = context or {}


class ValidationError(PDFTranslatorError):
    """Raised when input validation fails."""
    pass


class FileError(PDFTranslatorError):
    """Raised when file operations fail."""
    pass


class ProcessingError(PDFTranslatorError):
    """Raised when document processing fails."""
    pass


class TranslationError(PDFTranslatorError):
    """Raised when translation API calls fail."""
    pass


class ConfigurationError(PDFTranslatorError):
    """Raised when configuration is invalid or missing."""
    pass


class FontError(PDFTranslatorError):
    """Raised when font operations fail."""
    pass