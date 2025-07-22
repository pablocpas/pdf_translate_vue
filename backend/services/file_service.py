"""
File management service.

This service handles all file operations, replacing the scattered
file handling logic throughout the original backend code.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import UploadFile

from shared.config.base import Settings
from shared.models.exceptions import FileError, ValidationError
from shared.utils.file_utils import (
    ensure_directory_exists,
    is_valid_pdf,
    generate_unique_filename,
    get_safe_path,
    validate_file_size
)
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FileService:
    """
    Service for handling file operations.
    
    This consolidates all file-related logic that was scattered
    across the original backend endpoints.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the file service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.upload_dir = settings.upload_folder
        self.translated_dir = settings.translated_folder
        
        # Ensure directories exist
        ensure_directory_exists(self.upload_dir)
        ensure_directory_exists(self.translated_dir)
    
    async def save_uploaded_file(
        self, 
        file: UploadFile, 
        task_id: str
    ) -> Path:
        """
        Save an uploaded file to the uploads directory.
        
        Args:
            file: The uploaded file
            task_id: Unique task identifier
            
        Returns:
            Path: Path to the saved file
            
        Raises:
            ValidationError: If file validation fails
            FileError: If file save operation fails
        """
        # Validate file
        if not is_valid_pdf(file.filename):
            raise ValidationError(
                f"Invalid file type: {file.filename}. Only PDF files are supported.",
                code="INVALID_FILE_TYPE",
                context={"filename": file.filename}
            )
        
        # Validate file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        validate_file_size(file_size)
        
        # Generate safe filename
        filename = generate_unique_filename(file.filename, task_id)
        file_path = get_safe_path(self.upload_dir, filename)
        
        try:
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"File saved successfully: {file_path}")
            return file_path
            
        except IOError as e:
            raise FileError(
                f"Failed to save file: {str(e)}",
                code="FILE_SAVE_FAILED",
                context={"filename": filename, "path": str(file_path)}
            )
    
    def get_translation_data_path(self, task_id: str) -> Path:
        """
        Get the path to a translation data file.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Path: Path to the translation data file
        """
        filename = f"{task_id}_translation_data.json"
        return self.translated_dir / filename
    
    def load_translation_data(self, task_id: str) -> Dict[str, Any]:
        """
        Load translation data from file.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict[str, Any]: Translation data
            
        Raises:
            FileError: If file cannot be read or parsed
        """
        data_path = self.get_translation_data_path(task_id)
        
        if not data_path.exists():
            raise FileError(
                f"Translation data not found for task: {task_id}",
                code="TRANSLATION_DATA_NOT_FOUND",
                context={"task_id": task_id, "path": str(data_path)}
            )
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (IOError, json.JSONDecodeError) as e:
            raise FileError(
                f"Failed to load translation data: {str(e)}",
                code="TRANSLATION_DATA_LOAD_FAILED",
                context={"task_id": task_id, "path": str(data_path)}
            )
    
    def save_translation_data(
        self, 
        task_id: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Save translation data to file.
        
        Args:
            task_id: Task identifier
            data: Translation data to save
            
        Raises:
            FileError: If file cannot be saved
        """
        data_path = self.get_translation_data_path(task_id)
        
        try:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Translation data saved: {data_path}")
            
        except IOError as e:
            raise FileError(
                f"Failed to save translation data: {str(e)}",
                code="TRANSLATION_DATA_SAVE_FAILED",
                context={"task_id": task_id, "path": str(data_path)}
            )
    
    def get_translated_file_path(self, task_id: str) -> Path:
        """
        Get the path to a translated PDF file.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Path: Path to the translated file
        """
        filename = f"{task_id}_translated.pdf"
        return self.translated_dir / filename
    
    def file_exists(self, file_path: Path) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file exists
        """
        return file_path.exists() and file_path.is_file()
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict[str, Any]: File information
        """
        if not self.file_exists(file_path):
            return {"exists": False}
        
        stat = file_path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "name": file_path.name
        }