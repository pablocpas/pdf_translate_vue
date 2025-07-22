"""
File handling utilities.

This module centralizes file operations that were duplicated across
the original backend and worker code.
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from ..models.exceptions import FileError, ValidationError
from ..config.constants import SUPPORTED_FILE_EXTENSIONS, MAX_FILE_SIZE_MB


def ensure_directory_exists(directory_path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Raises:
        FileError: If directory creation fails
    """
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise FileError(
            f"Failed to create directory: {directory_path}",
            code="DIRECTORY_CREATION_FAILED",
            context={"path": str(directory_path), "error": str(e)}
        )


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: The filename
        
    Returns:
        str: The file extension (including the dot)
    """
    return Path(filename).suffix.lower()


def is_valid_pdf(filename: str) -> bool:
    """
    Check if a file has a valid PDF extension.
    
    Args:
        filename: The filename to check
        
    Returns:
        bool: True if the file has a valid PDF extension
    """
    extension = get_file_extension(filename)
    return extension in SUPPORTED_FILE_EXTENSIONS


def generate_unique_filename(original_filename: str, suffix: str = "") -> str:
    """
    Generate a unique filename based on the original.
    
    Args:
        original_filename: The original filename
        suffix: Optional suffix to add before the extension
        
    Returns:
        str: A unique filename
    """
    file_path = Path(original_filename)
    stem = file_path.stem
    extension = file_path.suffix
    unique_id = str(uuid.uuid4())[:8]
    
    if suffix:
        return f"{stem}_{suffix}_{unique_id}{extension}"
    return f"{stem}_{unique_id}{extension}"


def clean_filename(filename: str) -> str:
    """
    Clean a filename by removing/replacing problematic characters.
    
    Args:
        filename: The original filename
        
    Returns:
        str: A cleaned filename safe for filesystem use
    """
    # Remove or replace problematic characters
    cleaned = filename.replace(" ", "_")
    cleaned = "".join(c for c in cleaned if c.isalnum() or c in "._-")
    
    # Ensure it's not empty
    if not cleaned:
        cleaned = "file"
    
    return cleaned


def validate_file_size(file_size: int, max_size_mb: Optional[int] = None) -> None:
    """
    Validate that a file size is within acceptable limits.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum size in MB (uses default if None)
        
    Raises:
        ValidationError: If file size exceeds limit
    """
    max_size = (max_size_mb or MAX_FILE_SIZE_MB) * 1024 * 1024
    
    if file_size > max_size:
        raise ValidationError(
            f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds maximum "
            f"allowed size ({max_size / 1024 / 1024} MB)",
            code="FILE_TOO_LARGE",
            context={"file_size": file_size, "max_size": max_size}
        )


def get_safe_path(base_path: Path, filename: str) -> Path:
    """
    Get a safe file path, preventing directory traversal attacks.
    
    Args:
        base_path: Base directory path
        filename: Filename to join
        
    Returns:
        Path: Safe file path
        
    Raises:
        ValidationError: If path traversal is detected
    """
    # Clean the filename
    safe_filename = clean_filename(filename)
    
    # Create the full path
    full_path = base_path / safe_filename
    
    # Resolve to check for traversal attempts
    try:
        resolved_path = full_path.resolve()
        base_resolved = base_path.resolve()
        
        # Ensure the resolved path is within the base directory
        if not str(resolved_path).startswith(str(base_resolved)):
            raise ValidationError(
                "Path traversal attempt detected",
                code="PATH_TRAVERSAL_DETECTED",
                context={"filename": filename, "safe_filename": safe_filename}
            )
            
        return resolved_path
        
    except OSError as e:
        raise ValidationError(
            f"Invalid file path: {filename}",
            code="INVALID_PATH",
            context={"filename": filename, "error": str(e)}
        )