"""
Tests for FileService.

This module tests the file service functionality that was
extracted from the original monolithic backend.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import UploadFile
from io import BytesIO

from shared.models.exceptions import ValidationError, FileError
from services.file_service import FileService


class TestFileService:
    """Test suite for FileService."""
    
    def test_save_uploaded_file_success(self, file_service, sample_pdf_content):
        """Test successful file upload."""
        # Create mock uploaded file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read.return_value = sample_pdf_content
        
        # Test file save
        result = await file_service.save_uploaded_file(mock_file, "test_task_id")
        
        assert result.exists()
        assert result.name.endswith(".pdf")
        assert result.parent == file_service.upload_dir
    
    def test_save_uploaded_file_invalid_type(self, file_service):
        """Test file upload with invalid file type."""
        # Create mock uploaded file with invalid extension
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read.return_value = b"some text content"
        
        # Test validation error
        with pytest.raises(ValidationError) as exc_info:
            await file_service.save_uploaded_file(mock_file, "test_task_id")
        
        assert exc_info.value.code == "INVALID_FILE_TYPE"
    
    def test_save_uploaded_file_too_large(self, file_service):
        """Test file upload with oversized file."""
        # Create mock uploaded file that's too large
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large.pdf"
        mock_file.read.return_value = b"x" * (51 * 1024 * 1024)  # 51MB
        
        # Test validation error
        with pytest.raises(ValidationError) as exc_info:
            await file_service.save_uploaded_file(mock_file, "test_task_id")
        
        assert exc_info.value.code == "FILE_TOO_LARGE"
    
    def test_load_translation_data_success(self, file_service, sample_translation_data):
        """Test successful translation data loading."""
        task_id = "test_task"
        
        # Save test data
        file_service.save_translation_data(task_id, sample_translation_data)
        
        # Load and verify data
        loaded_data = file_service.load_translation_data(task_id)
        assert loaded_data == sample_translation_data
    
    def test_load_translation_data_not_found(self, file_service):
        """Test loading non-existent translation data."""
        with pytest.raises(FileError) as exc_info:
            file_service.load_translation_data("nonexistent_task")
        
        assert exc_info.value.code == "TRANSLATION_DATA_NOT_FOUND"
    
    def test_save_translation_data_success(self, file_service, sample_translation_data):
        """Test successful translation data saving."""
        task_id = "test_save_task"
        
        # Save data
        file_service.save_translation_data(task_id, sample_translation_data)
        
        # Verify file exists and contains correct data
        data_path = file_service.get_translation_data_path(task_id)
        assert data_path.exists()
        
        with open(data_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data == sample_translation_data
    
    def test_get_translated_file_path(self, file_service):
        """Test translated file path generation."""
        task_id = "test_task"
        
        path = file_service.get_translated_file_path(task_id)
        
        assert path.parent == file_service.translated_dir
        assert path.name == f"{task_id}_translated.pdf"
    
    def test_file_exists(self, file_service, sample_pdf_content):
        """Test file existence checking."""
        # Create a test file
        test_file = file_service.upload_dir / "test_exists.pdf"
        test_file.write_bytes(sample_pdf_content)
        
        # Test existence
        assert file_service.file_exists(test_file)
        assert not file_service.file_exists(Path("nonexistent.pdf"))
    
    def test_get_file_info(self, file_service, sample_pdf_content):
        """Test file information retrieval."""
        # Create a test file
        test_file = file_service.upload_dir / "test_info.pdf"
        test_file.write_bytes(sample_pdf_content)
        
        # Get file info
        info = file_service.get_file_info(test_file)
        
        assert info["exists"] is True
        assert info["size"] == len(sample_pdf_content)
        assert info["name"] == "test_info.pdf"
        assert "modified" in info
    
    def test_get_file_info_nonexistent(self, file_service):
        """Test file info for non-existent file."""
        info = file_service.get_file_info(Path("nonexistent.pdf"))
        assert info["exists"] is False