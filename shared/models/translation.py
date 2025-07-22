"""
Translation data models.

This module consolidates all translation-related data structures that were
previously defined inconsistently across the codebase.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from ..config.constants import TaskStatus, ModelType


class TranslationProgress(BaseModel):
    """Progress tracking for translation tasks."""
    current: int = Field(ge=0, description="Current step number")
    total: int = Field(gt=0, description="Total number of steps") 
    percent: int = Field(ge=0, le=100, description="Percentage completed")
    
    @validator("percent", pre=True, always=True)
    def calculate_percent(cls, v, values):
        """Auto-calculate percentage if not provided."""
        if v is None and "current" in values and "total" in values:
            current = values["current"]
            total = values["total"]
            if total > 0:
                return min(100, int((current / total) * 100))
        return v


class TextBlock(BaseModel):
    """Represents a text block extracted from a PDF page."""
    original_text: str = Field(description="Original text content")
    translated_text: Optional[str] = Field(None, description="Translated text")
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate") 
    width: float = Field(description="Block width")
    height: float = Field(description="Block height")
    font_size: Optional[float] = Field(None, description="Font size")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="OCR confidence")


class PageTranslation(BaseModel):
    """Represents translation data for a single page."""
    page_number: int = Field(ge=1, description="Page number (1-indexed)")
    original_language: Optional[str] = Field(None, description="Source language code")
    target_language: str = Field(description="Target language code")
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Text blocks")
    image_path: Optional[str] = Field(None, description="Path to page image")
    
    @validator("target_language")
    def validate_language_code(cls, v):
        """Validate language code format."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Language code must be at least 2 characters")
        return v.strip().lower()


class TranslationData(BaseModel):
    """Complete translation data for a document."""
    task_id: str = Field(description="Unique task identifier")
    original_filename: str = Field(description="Original PDF filename")
    source_language: Optional[str] = Field(None, description="Detected source language")
    target_language: str = Field(description="Target language for translation")
    model: ModelType = Field(description="Translation model used")
    pages: List[PageTranslation] = Field(default_factory=list, description="Page translations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("task_id")
    def validate_task_id(cls, v):
        """Ensure task ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        return v.strip()


class TranslationTask(BaseModel):
    """Represents a translation task with status and progress."""
    id: str = Field(description="Unique task identifier")
    status: TaskStatus = Field(description="Current task status")
    original_file: str = Field(description="Original filename")
    translated_file: Optional[str] = Field(None, description="Translated filename")
    error: Optional[str] = Field(None, description="Error message if failed")
    progress: Optional[TranslationProgress] = Field(None, description="Progress tracking")
    model: Optional[ModelType] = Field(None, description="Translation model")
    source_language: Optional[str] = Field(None, description="Source language")
    target_language: Optional[str] = Field(None, description="Target language")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    
    @validator("id")
    def validate_id(cls, v):
        """Ensure task ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        return v.strip()