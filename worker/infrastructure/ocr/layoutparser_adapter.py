"""
LayoutParser OCR adapter.

This module provides an adapter for LayoutParser functionality,
abstracting the OCR implementation from the business logic.
"""

from typing import List, Dict, Any
from PIL import Image
import numpy as np

from shared.models.task import TaskResult
from shared.models.exceptions import ProcessingError
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class LayoutParserAdapter:
    """
    Adapter for LayoutParser OCR functionality.
    
    This class provides a clean interface to LayoutParser,
    replacing the direct usage scattered throughout the original code.
    """
    
    def __init__(self):
        """Initialize the LayoutParser adapter."""
        self._model = None
        self._ocr_agent = None
        self._initialize_components()
    
    def _initialize_components(self):
        """
        Initialize LayoutParser components.
        
        This method handles the complex initialization that was
        embedded in the original processor code.
        """
        try:
            # Import LayoutParser components
            import layoutparser as lp
            
            # Initialize layout detection model
            # Note: This is a simplified version - in production you'd want
            # to handle model downloading, caching, etc.
            self._model = lp.Detectron2LayoutModel(
                'lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config',
                extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
                label_map={0: "TextRegion"}
            )
            
            # Initialize OCR agent
            self._ocr_agent = lp.TesseractAgent(languages='eng')
            
            logger.info("LayoutParser components initialized successfully")
            
        except ImportError as e:
            logger.error(f"LayoutParser not available: {str(e)}")
            self._model = None
            self._ocr_agent = None
        except Exception as e:
            logger.error(f"Failed to initialize LayoutParser: {str(e)}")
            self._model = None
            self._ocr_agent = None
    
    def extract_text_blocks(self, image: Image.Image) -> TaskResult:
        """
        Extract text blocks from an image using LayoutParser.
        
        Args:
            image: PIL Image to process
            
        Returns:
            TaskResult: Extraction result with text blocks
        """
        if not self._is_available():
            return self._fallback_ocr(image)
        
        try:
            # Convert PIL Image to numpy array
            image_array = np.array(image)
            
            # Detect layout
            layout = self._model.detect(image_array)
            
            # Extract text from detected regions
            text_blocks = []
            for i, block in enumerate(layout):
                # Get block coordinates
                x1, y1, x2, y2 = block.coordinates
                
                # Extract text from this region
                text_result = self._extract_text_from_block(image_array, block)
                if text_result.success:
                    text_info = text_result.data
                    
                    text_block = {
                        "block_id": i,
                        "original_text": text_info.get("text", ""),
                        "x": int(x1),
                        "y": int(y1),
                        "width": int(x2 - x1),
                        "height": int(y2 - y1),
                        "confidence": text_info.get("confidence", 0.0),
                        "block_type": block.type if hasattr(block, 'type') else "TextRegion"
                    }
                    
                    if text_block["original_text"].strip():
                        text_blocks.append(text_block)
            
            logger.debug(f"LayoutParser extracted {len(text_blocks)} text blocks")
            return TaskResult.success_result(
                data={"text_blocks": text_blocks},
                metadata={"extraction_method": "layoutparser", "blocks_detected": len(layout)}
            )
            
        except Exception as e:
            logger.error(f"LayoutParser extraction failed: {str(e)}")
            return self._fallback_ocr(image)
    
    def _extract_text_from_block(self, image_array: np.ndarray, block) -> TaskResult:
        """
        Extract text from a specific layout block.
        
        Args:
            image_array: Image as numpy array
            block: LayoutParser block object
            
        Returns:
            TaskResult: Text extraction result
        """
        try:
            # Crop image to block region
            x1, y1, x2, y2 = block.coordinates
            block_image = image_array[int(y1):int(y2), int(x1):int(x2)]
            
            # Use OCR agent to extract text
            text = self._ocr_agent.detect(block_image)
            
            return TaskResult.success_result(
                data={
                    "text": text,
                    "confidence": getattr(block, 'score', 0.8)  # Use detection confidence
                }
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="BLOCK_OCR_FAILED",
                error_message=f"Block OCR failed: {str(e)}"
            )
    
    def _fallback_ocr(self, image: Image.Image) -> TaskResult:
        """
        Fallback OCR using simple Tesseract.
        
        This method provides a fallback when LayoutParser is not available
        or fails, using the basic OCR from the original code.
        
        Args:
            image: PIL Image to process
            
        Returns:
            TaskResult: Fallback OCR result
        """
        logger.info("Using fallback OCR (Tesseract)")
        
        try:
            import pytesseract
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image, lang="eng")
            
            if not text.strip():
                return TaskResult.success_result(
                    data={"text_blocks": []},
                    metadata={"extraction_method": "tesseract_fallback", "note": "No text found"}
                )
            
            # Create a single text block covering the whole image
            text_block = {
                "block_id": 0,
                "original_text": text.strip(),
                "x": 0,
                "y": 0,
                "width": image.width,
                "height": image.height,
                "confidence": 0.7,  # Assume reasonable confidence
                "block_type": "TextRegion"
            }
            
            return TaskResult.success_result(
                data={"text_blocks": [text_block]},
                metadata={"extraction_method": "tesseract_fallback"}
            )
            
        except ImportError:
            return TaskResult.error_result(
                error_code="NO_OCR_AVAILABLE",
                error_message="Neither LayoutParser nor Tesseract is available"
            )
        except Exception as e:
            return TaskResult.error_result(
                error_code="FALLBACK_OCR_FAILED",
                error_message=f"Fallback OCR failed: {str(e)}"
            )
    
    def _is_available(self) -> bool:
        """Check if LayoutParser is available."""
        return self._model is not None and self._ocr_agent is not None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get information about OCR capabilities.
        
        Returns:
            Dict[str, Any]: Capability information
        """
        return {
            "layoutparser_available": self._is_available(),
            "fallback_available": self._is_tesseract_available(),
            "supported_formats": ["PIL.Image"],
            "features": {
                "layout_detection": self._is_available(),
                "text_extraction": True,
                "confidence_scores": self._is_available()
            }
        }
    
    def _is_tesseract_available(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            return True
        except ImportError:
            return False