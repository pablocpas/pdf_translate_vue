"""
Validation utilities.

This module provides common validation functions used across the application.
"""

from typing import Optional
from ..models.exceptions import ValidationError
from ..config.constants import SUPPORTED_LANGUAGES


def validate_language_code(language_code: str) -> str:
    """
    Validate and normalize a language code.
    
    Args:
        language_code: Language code to validate
        
    Returns:
        str: Normalized language code
        
    Raises:
        ValidationError: If language code is invalid
    """
    if not language_code:
        raise ValidationError(
            "Language code cannot be empty",
            code="EMPTY_LANGUAGE_CODE"
        )
    
    normalized_code = language_code.strip().lower()
    
    if normalized_code not in SUPPORTED_LANGUAGES:
        available_codes = list(SUPPORTED_LANGUAGES.keys())
        raise ValidationError(
            f"Unsupported language code: {language_code}. "
            f"Available codes: {', '.join(available_codes)}",
            code="UNSUPPORTED_LANGUAGE",
            context={
                "provided_code": language_code,
                "available_codes": available_codes
            }
        )
    
    return normalized_code


def validate_file_size(file_size: int, max_size_mb: Optional[int] = None) -> None:
    """
    Validate file size is within acceptable limits.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum size in MB (uses default if None)
        
    Raises:
        ValidationError: If file size exceeds limit
    """
    from ..config.constants import MAX_FILE_SIZE_MB
    
    max_size = (max_size_mb or MAX_FILE_SIZE_MB) * 1024 * 1024
    
    if file_size > max_size:
        raise ValidationError(
            f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds maximum "
            f"allowed size ({max_size / 1024 / 1024} MB)",
            code="FILE_TOO_LARGE",
            context={"file_size": file_size, "max_size": max_size}
        )


def validate_task_id(task_id: str) -> str:
    """
    Validate a task ID format.
    
    Args:
        task_id: Task ID to validate
        
    Returns:
        str: Normalized task ID
        
    Raises:
        ValidationError: If task ID is invalid
    """
    if not task_id or not task_id.strip():
        raise ValidationError(
            "Task ID cannot be empty",
            code="EMPTY_TASK_ID"
        )
    
    normalized_id = task_id.strip()
    
    # Basic format validation (adjust regex as needed)
    if len(normalized_id) < 3:
        raise ValidationError(
            "Task ID must be at least 3 characters long",
            code="INVALID_TASK_ID_LENGTH",
            context={"task_id": task_id}
        )
    
    return normalized_id