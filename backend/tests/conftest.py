"""
Pytest configuration and fixtures for backend tests.

This module provides shared test fixtures and configuration
to support comprehensive testing of the refactored backend.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from shared.config.base import Settings
from main import create_app
from services.file_service import FileService
from services.translation_service import TranslationService
from services.task_service import TaskService


@pytest.fixture
def test_settings():
    """Create test settings with temporary directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = Settings(
            openai_api_key="test_api_key",
            celery_broker_url="redis://localhost:6379/15",  # Test DB
            celery_result_backend="redis://localhost:6379/15",
            upload_folder=temp_path / "uploads",
            translated_folder=temp_path / "translated",
            temp_folder=temp_path / "temp",
            debug=True,
            log_level="DEBUG"
        )
        
        # Ensure directories exist
        settings.ensure_directories()
        yield settings


@pytest.fixture
def mock_celery_app():
    """Create a mock Celery application."""
    mock_app = Mock()
    mock_app.send_task.return_value = Mock(id="test_task_id")
    mock_app.control.revoke.return_value = True
    return mock_app


@pytest.fixture
def file_service(test_settings):
    """Create FileService with test settings."""
    return FileService(test_settings)


@pytest.fixture
def translation_service(test_settings, mock_celery_app):
    """Create TranslationService with test dependencies."""
    return TranslationService(test_settings, mock_celery_app)


@pytest.fixture
def task_service(mock_celery_app):
    """Create TaskService with mock Celery app."""
    return TaskService(mock_celery_app)


@pytest.fixture
def test_app(test_settings):
    """Create test FastAPI application."""
    with patch('backend.main.get_settings', return_value=test_settings):
        app = create_app()
        yield app


@pytest.fixture
def client(test_app):
    """Create test client for API testing."""
    return TestClient(test_app)


@pytest.fixture
def sample_pdf_content():
    """Provide sample PDF content for testing."""
    # Simple PDF content for testing
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
299
%%EOF"""


@pytest.fixture
def sample_translation_data():
    """Provide sample translation data for testing."""
    return {
        "pages": [
            {
                "page_number": 1,
                "translations": [
                    {
                        "original_text": "Hello World",
                        "translated_text": "Hola Mundo",
                        "target_language": "es"
                    }
                ]
            }
        ],
        "metadata": {
            "target_language": "es",
            "total_pages": 1
        }
    }


@pytest.fixture
def sample_position_data():
    """Provide sample position data for testing."""
    return {
        "pages": [
            {
                "page_number": 1,
                "positions": [
                    {
                        "x": 72,
                        "y": 720,
                        "width": 100,
                        "height": 20,
                        "font_size": 12,
                        "font_family": "OpenSans"
                    }
                ]
            }
        ]
    }