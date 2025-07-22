"""
Pytest configuration for worker tests.

This module provides test fixtures for worker component testing.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from shared.config.base import Settings
from core.orchestrator import TranslationOrchestrator
from core.document.analyzer import DocumentAnalyzer
from core.document.extractor import TextExtractor
from core.document.reconstructor import PDFReconstructor
from core.translation.translator import TranslationEngine
from core.fonts.manager import FontManager


@pytest.fixture
def test_settings():
    """Create test settings for worker tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = Settings(
            openai_api_key="test_api_key",
            upload_folder=temp_path / "uploads",
            translated_folder=temp_path / "translated", 
            temp_folder=temp_path / "temp",
            debug=True,
            log_level="DEBUG"
        )
        
        settings.ensure_directories()
        yield settings


@pytest.fixture
def mock_progress_callback():
    """Create a mock progress callback."""
    return Mock()


@pytest.fixture
def orchestrator(test_settings, mock_progress_callback):
    """Create TranslationOrchestrator for testing."""
    return TranslationOrchestrator(
        task_id="test_task",
        progress_callback=mock_progress_callback
    )


@pytest.fixture
def document_analyzer():
    """Create DocumentAnalyzer for testing."""
    return DocumentAnalyzer()


@pytest.fixture
def text_extractor():
    """Create TextExtractor for testing."""
    return TextExtractor()


@pytest.fixture
def pdf_reconstructor():
    """Create PDFReconstructor for testing."""
    return PDFReconstructor()


@pytest.fixture
def translation_engine():
    """Create TranslationEngine for testing."""
    return TranslationEngine()


@pytest.fixture
def font_manager():
    """Create FontManager for testing."""
    return FontManager()


@pytest.fixture
def sample_image():
    """Create a sample PIL image for testing."""
    from PIL import Image
    import numpy as np
    
    # Create a simple test image
    img_array = np.ones((100, 200, 3), dtype=np.uint8) * 255  # White image
    return Image.fromarray(img_array)


@pytest.fixture
def sample_text_blocks():
    """Provide sample text blocks for testing."""
    return [
        {
            "page_number": 1,
            "original_text": "Hello World",
            "x": 72,
            "y": 720,
            "width": 100,
            "height": 20,
            "font_size": 12,
            "confidence": 0.95
        },
        {
            "page_number": 1,
            "original_text": "This is a test",
            "x": 72,
            "y": 700,
            "width": 150,
            "height": 20,
            "font_size": 12,
            "confidence": 0.87
        }
    ]


@pytest.fixture
def sample_pages_data():
    """Provide sample page analysis data."""
    return [
        {
            "page_number": 1,
            "image_path": "/tmp/test_page_1.png",
            "width": 595,
            "height": 842,
            "layout_blocks": [],
            "source_pdf": "/tmp/test.pdf"
        }
    ]