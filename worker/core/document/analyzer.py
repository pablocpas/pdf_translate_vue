"""
Document analysis service.

This module handles PDF document analysis and layout detection,
extracting the complex analysis logic from the original processor.py.
"""

from pathlib import Path
from typing import List, Dict, Any
from pdf2image import convert_from_path

from shared.config import get_settings
from shared.models.task import TaskResult
from shared.models.exceptions import ProcessingError
from shared.utils.logging_utils import get_logger
from shared.utils.file_utils import ensure_directory_exists

logger = get_logger(__name__)


class DocumentAnalyzer:
    """
    Service for analyzing PDF documents and detecting layout structure.
    
    This class encapsulates the document analysis logic that was mixed
    with other concerns in the original processor.py file.
    """
    
    def __init__(self):
        """Initialize the document analyzer."""
        self.settings = get_settings()
        
    def analyze_document(self, pdf_path: str) -> TaskResult:
        """
        Analyze a PDF document and extract layout information.
        
        This method converts PDF pages to images for layout analysis,
        replacing the mixed logic in the original process_pdf function.
        
        Args:
            pdf_path: Path to the PDF file to analyze
            
        Returns:
            TaskResult: Analysis result with page data
        """
        logger.info(f"Starting document analysis: {pdf_path}")
        
        try:
            # Validate input file
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                return TaskResult.error_result(
                    error_code="FILE_NOT_FOUND",
                    error_message=f"PDF file not found: {pdf_path}"
                )
            
            # Convert PDF to images
            conversion_result = self._convert_pdf_to_images(pdf_path)
            if not conversion_result.success:
                return conversion_result
                
            images = conversion_result.data["images"]
            logger.info(f"PDF converted to {len(images)} page images")
            
            # Analyze each page
            pages_data = []
            for page_num, image in enumerate(images, 1):
                page_analysis = self._analyze_page(image, page_num, pdf_path)
                if not page_analysis.success:
                    return page_analysis
                    
                pages_data.append(page_analysis.data)
            
            logger.info(f"Document analysis completed: {len(pages_data)} pages")
            return TaskResult.success_result(
                data={"pages": pages_data},
                metadata={
                    "total_pages": len(pages_data),
                    "source_file": pdf_path
                }
            )
            
        except Exception as e:
            logger.error(f"Document analysis failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="DOCUMENT_ANALYSIS_FAILED",
                error_message=f"Document analysis failed: {str(e)}",
                traceback=str(e)
            )
    
    def _convert_pdf_to_images(self, pdf_path: str) -> TaskResult:
        """
        Convert PDF pages to images for analysis.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            TaskResult: Conversion result with images
        """
        try:
            # Convert PDF to images using the configured DPI
            images = convert_from_path(
                pdf_path,
                dpi=self.settings.dpi,
                fmt='RGB'
            )
            
            if not images:
                return TaskResult.error_result(
                    error_code="PDF_CONVERSION_FAILED",
                    error_message="No images generated from PDF"
                )
            
            return TaskResult.success_result(
                data={"images": images},
                metadata={"page_count": len(images)}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="PDF_CONVERSION_ERROR",
                error_message=f"PDF to image conversion failed: {str(e)}"
            )
    
    def _analyze_page(
        self, 
        image, 
        page_number: int, 
        source_pdf: str
    ) -> TaskResult:
        """
        Analyze a single page image for layout structure.
        
        Args:
            image: PIL Image object
            page_number: Page number (1-indexed)
            source_pdf: Source PDF path for reference
            
        Returns:
            TaskResult: Page analysis result
        """
        try:
            # Save page image for later use
            image_path = self._save_page_image(image, page_number, source_pdf)
            
            # For now, we'll return basic page information
            # In a full implementation, this would use LayoutParser
            # to detect text blocks, images, tables, etc.
            page_data = {
                "page_number": page_number,
                "image_path": str(image_path),
                "width": image.width,
                "height": image.height,
                "layout_blocks": [],  # Would be populated by LayoutParser
                "source_pdf": source_pdf
            }
            
            logger.debug(f"Page {page_number} analyzed: {image.width}x{image.height}")
            return TaskResult.success_result(data=page_data)
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="PAGE_ANALYSIS_FAILED",
                error_message=f"Page {page_number} analysis failed: {str(e)}"
            )
    
    def _save_page_image(self, image, page_number: int, source_pdf: str) -> Path:
        """
        Save page image to temporary directory.
        
        Args:
            image: PIL Image object
            page_number: Page number
            source_pdf: Source PDF path
            
        Returns:
            Path: Path to saved image
        """
        # Ensure temp directory exists
        temp_dir = self.settings.temp_folder
        ensure_directory_exists(temp_dir)
        
        # Generate image filename
        pdf_name = Path(source_pdf).stem
        image_filename = f"{pdf_name}_page_{page_number}.png"
        image_path = temp_dir / image_filename
        
        # Save image
        image.save(image_path, 'PNG')
        
        return image_path
    
    def get_page_dimensions(self, pdf_path: str) -> TaskResult:
        """
        Get dimensions of all pages in a PDF.
        
        This is a utility method that can be used without full analysis.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            TaskResult: Page dimensions data
        """
        try:
            # Convert just the first page to get dimensions
            # In a production system, you might use a PDF library directly
            images = convert_from_path(pdf_path, dpi=72, first_page=1, last_page=1)
            
            if not images:
                return TaskResult.error_result(
                    error_code="NO_PAGES_FOUND",
                    error_message="No pages found in PDF"
                )
            
            # For simplicity, assume all pages have the same dimensions
            # In reality, you'd analyze each page
            first_image = images[0]
            
            return TaskResult.success_result(
                data={
                    "width": first_image.width,
                    "height": first_image.height,
                    "aspect_ratio": first_image.width / first_image.height
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="DIMENSION_ANALYSIS_FAILED",
                error_message=f"Failed to get page dimensions: {str(e)}"
            )