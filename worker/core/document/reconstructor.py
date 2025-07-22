"""
PDF reconstruction service.

This module handles PDF generation with translated content,
extracting the complex reconstruction logic from the original processor.py.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

from shared.config import get_settings
from shared.models.task import TaskResult
from shared.models.exceptions import ProcessingError
from shared.utils.logging_utils import get_logger
from shared.config.constants import MIN_FONT_SIZE, FONT_SCALE_FACTOR

logger = get_logger(__name__)


class PDFReconstructor:
    """
    Service for reconstructing PDF documents with translated content.
    
    This class consolidates the PDF generation logic that was mixed
    with other concerns in the original processor.py file.
    """
    
    def __init__(self):
        """Initialize the PDF reconstructor."""
        self.settings = get_settings()
    
    def reconstruct_pdf(
        self,
        pages_data: List[Dict[str, Any]],
        translated_blocks: List[Dict[str, Any]],
        output_path: Path,
        target_language: str
    ) -> TaskResult:
        """
        Reconstruct PDF with translated content.
        
        This method replaces the complex PDF generation logic that was
        embedded in the original processor.py file.
        
        Args:
            pages_data: Original page analysis data
            translated_blocks: Translated text blocks with positions
            output_path: Path for output PDF
            target_language: Target language code
            
        Returns:
            TaskResult: Reconstruction result
        """
        logger.info(f"Starting PDF reconstruction: {output_path}")
        
        try:
            # Group translated blocks by page
            blocks_by_page = self._group_blocks_by_page(translated_blocks)
            
            # Create PDF canvas
            pdf_canvas = canvas.Canvas(str(output_path), pagesize=A4)
            
            # Process each page
            pages_processed = 0
            for page_data in pages_data:
                page_num = page_data.get("page_number", 1)
                
                result = self._reconstruct_page(
                    pdf_canvas=pdf_canvas,
                    page_data=page_data,
                    translated_blocks=blocks_by_page.get(page_num, []),
                    target_language=target_language
                )
                
                if not result.success:
                    pdf_canvas.save()  # Save what we have so far
                    return result
                
                pages_processed += 1
                logger.debug(f"Page {page_num} reconstructed successfully")
            
            # Save PDF
            pdf_canvas.save()
            
            logger.info(f"PDF reconstruction completed: {pages_processed} pages")
            return TaskResult.success_result(
                data={
                    "output_path": str(output_path),
                    "pages_processed": pages_processed
                },
                metadata={
                    "target_language": target_language,
                    "total_blocks": len(translated_blocks)
                }
            )
            
        except Exception as e:
            logger.error(f"PDF reconstruction failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="PDF_RECONSTRUCTION_FAILED",
                error_message=f"PDF reconstruction failed: {str(e)}",
                traceback=str(e)
            )
    
    def _group_blocks_by_page(
        self, 
        translated_blocks: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Group translated blocks by page number.
        
        Args:
            translated_blocks: List of translated text blocks
            
        Returns:
            Dict[int, List[Dict[str, Any]]]: Blocks grouped by page
        """
        blocks_by_page = {}
        
        for block in translated_blocks:
            page_num = block.get("page_number", 1)
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)
        
        return blocks_by_page
    
    def _reconstruct_page(
        self,
        pdf_canvas: canvas.Canvas,
        page_data: Dict[str, Any],
        translated_blocks: List[Dict[str, Any]],
        target_language: str
    ) -> TaskResult:
        """
        Reconstruct a single page with translated content.
        
        Args:
            pdf_canvas: ReportLab canvas object
            page_data: Original page data
            translated_blocks: Translated blocks for this page
            target_language: Target language code
            
        Returns:
            TaskResult: Page reconstruction result
        """
        try:
            page_num = page_data.get("page_number", 1)
            
            # Add background image if available
            image_path = page_data.get("image_path")
            if image_path and Path(image_path).exists():
                self._add_background_image(pdf_canvas, image_path)
            
            # Add translated text blocks
            blocks_added = 0
            for block in translated_blocks:
                result = self._add_text_block(pdf_canvas, block, target_language)
                if result.success:
                    blocks_added += 1
                else:
                    logger.warning(f"Failed to add text block: {result.error.message}")
            
            # Finish page
            pdf_canvas.showPage()
            
            logger.debug(f"Page {page_num}: {blocks_added}/{len(translated_blocks)} blocks added")
            return TaskResult.success_result(
                data={"blocks_added": blocks_added},
                metadata={"page_number": page_num}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="PAGE_RECONSTRUCTION_FAILED",
                error_message=f"Page reconstruction failed: {str(e)}"
            )
    
    def _add_background_image(
        self, 
        pdf_canvas: canvas.Canvas, 
        image_path: str
    ) -> None:
        """
        Add background image to the PDF page.
        
        Args:
            pdf_canvas: ReportLab canvas
            image_path: Path to background image
        """
        try:
            # Load and add image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get page dimensions
                page_width, page_height = A4
                
                # Calculate scaling to fit page
                img_width, img_height = img.size
                scale_x = page_width / img_width
                scale_y = page_height / img_height
                scale = min(scale_x, scale_y)
                
                # Calculate centered position
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                x = (page_width - scaled_width) / 2
                y = (page_height - scaled_height) / 2
                
                # Add image to canvas
                img_reader = ImageReader(img)
                pdf_canvas.drawImage(
                    img_reader,
                    x, y,
                    width=scaled_width,
                    height=scaled_height
                )
                
        except Exception as e:
            logger.warning(f"Failed to add background image: {str(e)}")
    
    def _add_text_block(
        self,
        pdf_canvas: canvas.Canvas,
        text_block: Dict[str, Any],
        target_language: str
    ) -> TaskResult:
        """
        Add a translated text block to the PDF.
        
        Args:
            pdf_canvas: ReportLab canvas
            text_block: Text block with position and content
            target_language: Target language code
            
        Returns:
            TaskResult: Text addition result
        """
        try:
            # Extract text and position
            text = text_block.get("translated_text", "").strip()
            if not text:
                return TaskResult.success_result(
                    metadata={"skipped": "empty_text"}
                )
            
            x = text_block.get("x", 0)
            y = text_block.get("y", 0)
            width = text_block.get("width", 100)
            height = text_block.get("height", 20)
            original_font_size = text_block.get("font_size", 12)
            
            # Get appropriate font for language
            font_name = self._get_font_for_language(target_language)
            
            # Calculate appropriate font size
            font_size = self._calculate_font_size(
                text, width, height, original_font_size
            )
            
            # Convert coordinates (PDF uses bottom-left origin)
            page_height = A4[1]
            pdf_y = page_height - y - height
            
            # Set font and draw text
            pdf_canvas.setFont(font_name, font_size)
            
            # Handle text that might be too long for the space
            if len(text) * font_size * 0.6 > width:  # Rough text width estimation
                # Use paragraph for text wrapping
                self._draw_wrapped_text(
                    pdf_canvas, text, x, pdf_y, width, height, font_name, font_size
                )
            else:
                # Simple text drawing
                pdf_canvas.drawString(x, pdf_y + height - font_size, text)
            
            return TaskResult.success_result(
                data={"text_added": True},
                metadata={
                    "font": font_name,
                    "font_size": font_size,
                    "position": {"x": x, "y": pdf_y}
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="TEXT_BLOCK_ADD_FAILED",
                error_message=f"Failed to add text block: {str(e)}"
            )
    
    def _get_font_for_language(self, language_code: str) -> str:
        """
        Get appropriate font for language.
        
        Args:
            language_code: Language code
            
        Returns:
            str: Font name
        """
        from shared.config.constants import FONT_MAPPING
        return FONT_MAPPING.get(language_code.lower(), "OpenSans")
    
    def _calculate_font_size(
        self,
        text: str,
        available_width: float,
        available_height: float,
        original_font_size: float
    ) -> float:
        """
        Calculate appropriate font size for text block.
        
        Args:
            text: Text to fit
            available_width: Available width
            available_height: Available height
            original_font_size: Original font size
            
        Returns:
            float: Calculated font size
        """
        # Start with scaled original font size
        font_size = original_font_size * FONT_SCALE_FACTOR
        
        # Ensure minimum font size
        font_size = max(font_size, MIN_FONT_SIZE)
        
        # Rough estimation of text width (0.6 * font_size per character)
        estimated_width = len(text) * font_size * 0.6
        
        # Scale down if text is too wide
        if estimated_width > available_width:
            font_size = font_size * (available_width / estimated_width)
        
        # Ensure text fits in height
        if font_size > available_height * 0.8:  # Leave some margin
            font_size = available_height * 0.8
        
        # Final minimum size check
        return max(font_size, MIN_FONT_SIZE)
    
    def _draw_wrapped_text(
        self,
        pdf_canvas: canvas.Canvas,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
        font_name: str,
        font_size: float
    ) -> None:
        """
        Draw text with wrapping support.
        
        Args:
            pdf_canvas: ReportLab canvas
            text: Text to draw
            x, y: Position
            width, height: Available space
            font_name: Font to use
            font_size: Font size
        """
        try:
            # Create paragraph style
            style = ParagraphStyle(
                name='CustomStyle',
                fontName=font_name,
                fontSize=font_size,
                leading=font_size * 1.2,  # Line spacing
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0,
            )
            
            # Create paragraph
            paragraph = Paragraph(text, style)
            
            # Calculate paragraph size
            para_width, para_height = paragraph.wrapOn(pdf_canvas, width, height)
            
            # Draw paragraph if it fits
            if para_height <= height:
                paragraph.drawOn(pdf_canvas, x, y + height - para_height)
            else:
                # Fallback: draw simple text, truncated if necessary
                max_chars = int(width / (font_size * 0.6))
                truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text
                pdf_canvas.drawString(x, y + height - font_size, truncated_text)
                
        except Exception as e:
            logger.warning(f"Wrapped text drawing failed, using simple text: {str(e)}")
            # Fallback to simple text
            pdf_canvas.drawString(x, y + height - font_size, text[:50])
    
    def regenerate_pdf_with_updates(
        self,
        translation_data: Dict[str, Any],
        position_data: Dict[str, Any],
        output_path: Path,
        target_language: str
    ) -> TaskResult:
        """
        Regenerate PDF with updated translation data.
        
        This method handles regeneration when users edit translations,
        replacing the complex regeneration logic in the original code.
        
        Args:
            translation_data: Updated translation data
            position_data: Position data for text blocks
            output_path: Output PDF path
            target_language: Target language code
            
        Returns:
            TaskResult: Regeneration result
        """
        logger.info(f"Starting PDF regeneration: {output_path}")
        
        try:
            # Convert translation and position data to blocks format
            conversion_result = self._convert_update_data_to_blocks(
                translation_data, position_data
            )
            if not conversion_result.success:
                return conversion_result
            
            pages_data = conversion_result.data["pages_data"]
            text_blocks = conversion_result.data["text_blocks"]
            
            # Use existing reconstruction logic
            return self.reconstruct_pdf(
                pages_data=pages_data,
                translated_blocks=text_blocks,
                output_path=output_path,
                target_language=target_language
            )
            
        except Exception as e:
            logger.error(f"PDF regeneration failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="PDF_REGENERATION_FAILED",
                error_message=f"PDF regeneration failed: {str(e)}",
                traceback=str(e)
            )
    
    def _convert_update_data_to_blocks(
        self,
        translation_data: Dict[str, Any],
        position_data: Dict[str, Any]
    ) -> TaskResult:
        """
        Convert update data from frontend to internal block format.
        
        Args:
            translation_data: Translation data from frontend
            position_data: Position data from frontend
            
        Returns:
            TaskResult: Conversion result
        """
        try:
            pages_data = []
            text_blocks = []
            
            translation_pages = translation_data.get("pages", [])
            position_pages = position_data.get("pages", [])
            
            # Create lookup for position data
            position_lookup = {}
            for pos_page in position_pages:
                page_num = pos_page.get("page_number", 1)
                position_lookup[page_num] = pos_page.get("positions", [])
            
            # Process each page
            for trans_page in translation_pages:
                page_num = trans_page.get("page_number", 1)
                translations = trans_page.get("translations", [])
                positions = position_lookup.get(page_num, [])
                
                # Create page data
                page_data = {
                    "page_number": page_num,
                    "image_path": "",  # Would need to be provided or looked up
                    "width": 595,     # A4 width in points
                    "height": 842     # A4 height in points
                }
                pages_data.append(page_data)
                
                # Create text blocks
                for i, translation in enumerate(translations):
                    position = positions[i] if i < len(positions) else {}
                    
                    text_block = {
                        "page_number": page_num,
                        "original_text": translation.get("original_text", ""),
                        "translated_text": translation.get("translated_text", ""),
                        "x": position.get("x", 0),
                        "y": position.get("y", 0),
                        "width": position.get("width", 100),
                        "height": position.get("height", 20),
                        "font_size": position.get("font_size", 12),
                        "target_language": translation.get("target_language", target_language)
                    }
                    text_blocks.append(text_block)
            
            return TaskResult.success_result(
                data={
                    "pages_data": pages_data,
                    "text_blocks": text_blocks
                },
                metadata={
                    "pages_processed": len(pages_data),
                    "blocks_created": len(text_blocks)
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="UPDATE_DATA_CONVERSION_FAILED",
                error_message=f"Failed to convert update data: {str(e)}"
            )
    
    def validate_output_pdf(self, pdf_path: Path) -> TaskResult:
        """
        Validate the generated PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            TaskResult: Validation result
        """
        try:
            if not pdf_path.exists():
                return TaskResult.error_result(
                    error_code="PDF_NOT_FOUND",
                    error_message=f"Generated PDF not found: {pdf_path}"
                )
            
            # Check file size
            file_size = pdf_path.stat().st_size
            if file_size < 1024:  # Less than 1KB is probably invalid
                return TaskResult.error_result(
                    error_code="PDF_TOO_SMALL",
                    error_message=f"Generated PDF is too small: {file_size} bytes"
                )
            
            # Basic PDF header check
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    return TaskResult.error_result(
                        error_code="INVALID_PDF_FORMAT",
                        error_message="Generated file is not a valid PDF"
                    )
            
            return TaskResult.success_result(
                data={
                    "valid": True,
                    "file_size": file_size,
                    "path": str(pdf_path)
                },
                metadata={"validation_passed": True}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="PDF_VALIDATION_FAILED",
                error_message=f"PDF validation failed: {str(e)}"
            )