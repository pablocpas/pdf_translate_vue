"""Shared data models for PDF Translator."""

from .translation import (
    TranslationTask,
    TranslationProgress,
    TranslationData,
    PageTranslation,
    TextBlock
)
from .task import TaskResult, TaskError
from .exceptions import (
    PDFTranslatorError,
    ValidationError,
    ProcessingError,
    TranslationError,
    FileError
)

__all__ = [
    "TranslationTask",
    "TranslationProgress", 
    "TranslationData",
    "PageTranslation",
    "TextBlock",
    "TaskResult",
    "TaskError",
    "PDFTranslatorError",
    "ValidationError",
    "ProcessingError", 
    "TranslationError",
    "FileError"
]