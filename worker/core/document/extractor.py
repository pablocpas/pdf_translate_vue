"""
Text extraction service.

This module handles OCR and text extraction from PDF pages,
separating this concern from the original mixed processor logic.
"""

from typing import List, Dict, Any
from PIL import Image
import os

from shared.models.task import TaskResult
from shared.models.exceptions import ProcessingError
from shared.utils.logging_utils import get_logger
from infrastructure.ocr.layoutparser_adapter import LayoutParserAdapter

logger = get_logger(__name__)


class TextExtractor:
    """
    Service for extracting text from document pages.
    
    This class encapsulates OCR and text extraction logic that was
    embedded in the original processor.py file.
    """
    
    def __init__(self):
        """Initialize the text extractor."""
        self.ocr_adapter = LayoutParserAdapter()
    
    def extract_text_from_pages(self, pages_data: List[Dict[str, Any]]) -> TaskResult:
        """
        Extract text from multiple pages.
        
        Args:
            pages_data: List of page analysis data
            
        Returns:
            TaskResult: Extraction result with text blocks
        """
        logger.info(f"Starting text extraction from {len(pages_data)} pages")
        
        try:
            all_text_blocks = []
            
            for page_data in pages_data:
                page_num = page_data.get("page_number", 1)
                image_path = page_data.get("image_path")
                
                if not image_path or not os.path.exists(image_path):
                    logger.warning(f"Page {page_num}: Image not found at {image_path}")
                    continue
                
                # Extract text from this page
                extraction_result = self._extract_text_from_page(page_data)
                if not extraction_result.success:
                    logger.error(f"Page {page_num}: Text extraction failed")
                    continue
                
                page_blocks = extraction_result.data.get("text_blocks", [])
                all_text_blocks.extend(page_blocks)
                logger.debug(f"Page {page_num}: Extracted {len(page_blocks)} text blocks")
            
            logger.info(f"Text extraction completed: {len(all_text_blocks)} total blocks")
            return TaskResult.success_result(
                data={"text_blocks": all_text_blocks},
                metadata={
                    "pages_processed": len(pages_data),
                    "total_blocks": len(all_text_blocks)
                }
            )
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="TEXT_EXTRACTION_FAILED",
                error_message=f"Text extraction failed: {str(e)}",
                traceback=str(e)
            )
    
    def _extract_text_from_page(self, page_data: Dict[str, Any]) -> TaskResult:
        """
        Extract text from a single page.
        
        Args:
            page_data: Page analysis data
            
        Returns:
            TaskResult: Page text extraction result
        """
        try:
            page_number = page_data.get("page_number", 1)
            image_path = page_data.get("image_path")
            
            # Load image
            try:
                image = Image.open(image_path)
            except Exception as e:
                return TaskResult.error_result(
                    error_code="IMAGE_LOAD_FAILED",
                    error_message=f"Failed to load page image: {str(e)}"
                )
            
            # Extract text using OCR adapter
            ocr_result = self.ocr_adapter.extract_text_blocks(image)
            if not ocr_result.success:
                return ocr_result
            
            # Add page number to each text block
            text_blocks = ocr_result.data.get("text_blocks", [])
            for block in text_blocks:
                block["page_number"] = page_number
                block["source_image"] = image_path
            
            return TaskResult.success_result(
                data={"text_blocks": text_blocks},
                metadata={
                    "page_number": page_number,
                    "blocks_found": len(text_blocks)
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="PAGE_TEXT_EXTRACTION_FAILED",
                error_message=f"Page text extraction failed: {str(e)}"
            )
    
    def extract_text_from_region(
        self,
        image_path: str,
        x: int, y: int, width: int, height: int
    ) -> TaskResult:
        """
        Extract text from a specific region of an image.
        
        This method can be used for targeted text extraction
        from specific areas of a document.
        
        Args:
            image_path: Path to the image file
            x, y: Top-left coordinates of the region
            width, height: Region dimensions
            
        Returns:
            TaskResult: Region text extraction result
        """
        try:
            # Load and crop image
            image = Image.open(image_path)
            cropped_image = image.crop((x, y, x + width, y + height))
            
            # Extract text from cropped region
            ocr_result = self.ocr_adapter.extract_text_blocks(cropped_image)
            if not ocr_result.success:
                return ocr_result
            
            # Adjust coordinates back to original image space
            text_blocks = ocr_result.data.get("text_blocks", [])
            for block in text_blocks:
                block["x"] = block.get("x", 0) + x
                block["y"] = block.get("y", 0) + y
            
            return TaskResult.success_result(
                data={"text_blocks": text_blocks},
                metadata={"region": {"x": x, "y": y, "width": width, "height": height}}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="REGION_TEXT_EXTRACTION_FAILED",
                error_message=f"Region text extraction failed: {str(e)}"
            )
    
    def validate_text_quality(self, text_blocks: List[Dict[str, Any]]) -> TaskResult:
        """
        Validate the quality of extracted text.
        
        This method can be used to filter out low-quality OCR results.
        
        Args:
            text_blocks: List of text blocks to validate
            
        Returns:
            TaskResult: Validation result with quality metrics
        """
        try:
            if not text_blocks:
                return TaskResult.success_result(
                    data={"quality_score": 0.0, "valid_blocks": []},
                    metadata={"message": "No text blocks to validate"}
                )
            
            valid_blocks = []
            total_confidence = 0.0
            
            for block in text_blocks:
                text = block.get("original_text", "").strip()
                confidence = block.get("confidence", 0.0)
                
                # Basic quality checks
                if (len(text) >= 2 and  # Minimum length
                    confidence >= 0.5 and  # Minimum confidence
                    not text.isdigit() and  # Skip pure numbers
                    any(c.isalpha() for c in text)):  # Contains letters
                    
                    valid_blocks.append(block)
                    total_confidence += confidence
            
            avg_confidence = (total_confidence / len(valid_blocks)) if valid_blocks else 0.0
            quality_score = min(1.0, avg_confidence * (len(valid_blocks) / len(text_blocks)))
            
            return TaskResult.success_result(
                data={
                    "quality_score": quality_score,
                    "valid_blocks": valid_blocks
                },
                metadata={
                    "total_blocks": len(text_blocks),
                    "valid_blocks": len(valid_blocks),
                    "average_confidence": avg_confidence
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="TEXT_QUALITY_VALIDATION_FAILED",
                error_message=f"Text quality validation failed: {str(e)}"
            )