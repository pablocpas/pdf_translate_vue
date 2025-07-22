"""
Translation engine service.

This module provides the core translation functionality, refactored
from the original scattered translation logic.
"""

from typing import List, Dict, Any
from pydantic import BaseModel

from shared.config import get_settings
from shared.models.task import TaskResult
from shared.models.exceptions import TranslationError
from shared.utils.logging_utils import get_logger
from shared.utils.validation import validate_language_code

from .models.openai_client import OpenAITranslationClient
from .language_detector import LanguageDetector

logger = get_logger(__name__)


class TranslationResponse(BaseModel):
    """Structured response for translation API calls."""
    translations: List[str]


class TranslationEngine:
    """
    Core translation service.
    
    This class encapsulates all translation logic that was scattered
    throughout the original codebase, providing a clean interface
    for text translation operations.
    """
    
    def __init__(self):
        """Initialize the translation engine."""
        self.settings = get_settings()
        self.client = OpenAITranslationClient()
        self.language_detector = LanguageDetector()
    
    def translate_text_blocks(
        self,
        text_blocks: List[Dict[str, Any]],
        target_language: str,
        model: str = None
    ) -> TaskResult:
        """
        Translate a list of text blocks.
        
        This method replaces the complex translation logic that was
        embedded in the original processor.py file.
        
        Args:
            text_blocks: List of text blocks with position information
            target_language: Target language code
            model: Translation model to use (optional)
            
        Returns:
            TaskResult: Translation result with translated blocks
        """
        logger.info(f"Starting translation of {len(text_blocks)} text blocks to {target_language}")
        
        try:
            # Validate target language
            target_language = validate_language_code(target_language)
            
            # Extract texts for translation
            texts_to_translate = []
            block_indices = []
            
            for i, block in enumerate(text_blocks):
                original_text = block.get("original_text", "").strip()
                if original_text:
                    texts_to_translate.append(original_text)
                    block_indices.append(i)
            
            if not texts_to_translate:
                logger.warning("No text found to translate")
                return TaskResult.success_result(
                    data={"translated_blocks": []},
                    metadata={"message": "No text blocks contained translatable text"}
                )
            
            # Perform batch translation
            translation_result = self._translate_batch(
                texts=texts_to_translate,
                target_language=target_language,
                model=model
            )
            
            if not translation_result.success:
                return translation_result
            
            translations = translation_result.data["translations"]
            
            # Combine translations back with original blocks
            translated_blocks = []
            translation_index = 0
            
            for i, block in enumerate(text_blocks):
                translated_block = block.copy()
                
                if i in block_indices and translation_index < len(translations):
                    translated_block["translated_text"] = translations[translation_index]
                    translated_block["target_language"] = target_language
                    translation_index += 1
                else:
                    translated_block["translated_text"] = block.get("original_text", "")
                    translated_block["target_language"] = target_language
                
                translated_blocks.append(translated_block)
            
            logger.info(f"Translation completed: {len(translations)} texts translated")
            return TaskResult.success_result(
                data={"translated_blocks": translated_blocks},
                metadata={
                    "total_blocks": len(text_blocks),
                    "translated_texts": len(translations),
                    "target_language": target_language,
                    "model": model or self.settings.gpt_model
                }
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="TRANSLATION_FAILED",
                error_message=f"Translation failed: {str(e)}",
                traceback=str(e)
            )
    
    def _translate_batch(
        self,
        texts: List[str],
        target_language: str,
        model: str = None
    ) -> TaskResult:
        """
        Translate a batch of texts.
        
        This method handles the actual API calls and implements
        the batching logic that was in the original translator.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            model: Translation model to use
            
        Returns:
            TaskResult: Translation result
        """
        try:
            # Use configured model if none specified
            translation_model = model or self.settings.gpt_model
            
            # For large batches, split into smaller chunks
            batch_size = 10  # Process 10 texts at a time
            all_translations = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Translate this batch
                batch_result = self.client.translate_texts(
                    texts=batch_texts,
                    target_language=target_language,
                    model=translation_model
                )
                
                if not batch_result.success:
                    # If batch translation fails, try individual texts
                    individual_results = self._translate_individually(
                        batch_texts, target_language, translation_model
                    )
                    if not individual_results.success:
                        return individual_results
                    all_translations.extend(individual_results.data["translations"])
                else:
                    all_translations.extend(batch_result.data["translations"])
                
                logger.debug(f"Translated batch {i//batch_size + 1}: {len(batch_texts)} texts")
            
            return TaskResult.success_result(
                data={"translations": all_translations},
                metadata={"batches_processed": (len(texts) + batch_size - 1) // batch_size}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="BATCH_TRANSLATION_FAILED",
                error_message=f"Batch translation failed: {str(e)}"
            )
    
    def _translate_individually(
        self,
        texts: List[str],
        target_language: str,
        model: str
    ) -> TaskResult:
        """
        Translate texts individually as fallback.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            model: Translation model to use
            
        Returns:
            TaskResult: Individual translation results
        """
        translations = []
        failed_count = 0
        
        for text in texts:
            try:
                result = self.client.translate_texts(
                    texts=[text],
                    target_language=target_language,
                    model=model
                )
                
                if result.success and result.data["translations"]:
                    translations.append(result.data["translations"][0])
                else:
                    # If translation fails, use original text
                    translations.append(text)
                    failed_count += 1
                    logger.warning(f"Individual translation failed, using original text: {text[:50]}...")
                    
            except Exception as e:
                translations.append(text)
                failed_count += 1
                logger.warning(f"Translation error for text '{text[:50]}...': {str(e)}")
        
        if failed_count > 0:
            logger.warning(f"Failed to translate {failed_count}/{len(texts)} texts")
        
        return TaskResult.success_result(
            data={"translations": translations},
            metadata={"failed_translations": failed_count}
        )
    
    def detect_source_language(self, text_samples: List[str]) -> TaskResult:
        """
        Detect the source language of text samples.
        
        Args:
            text_samples: Sample texts for language detection
            
        Returns:
            TaskResult: Language detection result
        """
        try:
            if not text_samples:
                return TaskResult.error_result(
                    error_code="NO_TEXT_SAMPLES",
                    error_message="No text samples provided for language detection"
                )
            
            # Use language detector
            detection_result = self.language_detector.detect_language(text_samples)
            return detection_result
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="LANGUAGE_DETECTION_FAILED",
                error_message=f"Language detection failed: {str(e)}"
            )
    
    def validate_translation_quality(
        self,
        original_texts: List[str],
        translated_texts: List[str],
        target_language: str
    ) -> TaskResult:
        """
        Validate the quality of translations.
        
        This method can be used to assess translation quality
        and identify potential issues.
        
        Args:
            original_texts: Original text list
            translated_texts: Translated text list
            target_language: Target language code
            
        Returns:
            TaskResult: Quality assessment result
        """
        try:
            if len(original_texts) != len(translated_texts):
                return TaskResult.error_result(
                    error_code="TRANSLATION_COUNT_MISMATCH",
                    error_message="Number of original and translated texts don't match"
                )
            
            quality_metrics = {
                "total_pairs": len(original_texts),
                "empty_translations": 0,
                "identical_translations": 0,
                "average_length_ratio": 0.0,
                "suspicious_translations": []
            }
            
            total_length_ratio = 0.0
            
            for i, (original, translated) in enumerate(zip(original_texts, translated_texts)):
                # Check for empty translations
                if not translated.strip():
                    quality_metrics["empty_translations"] += 1
                    quality_metrics["suspicious_translations"].append({
                        "index": i,
                        "issue": "empty_translation",
                        "original": original[:100]
                    })
                
                # Check for identical texts (possible translation failure)
                elif original.strip() == translated.strip():
                    quality_metrics["identical_translations"] += 1
                    quality_metrics["suspicious_translations"].append({
                        "index": i,
                        "issue": "identical_text",
                        "text": original[:100]
                    })
                
                # Calculate length ratio
                if len(original) > 0:
                    length_ratio = len(translated) / len(original)
                    total_length_ratio += length_ratio
                    
                    # Flag unusually short or long translations
                    if length_ratio < 0.3 or length_ratio > 3.0:
                        quality_metrics["suspicious_translations"].append({
                            "index": i,
                            "issue": "unusual_length_ratio",
                            "ratio": length_ratio,
                            "original": original[:100],
                            "translated": translated[:100]
                        })
            
            # Calculate average length ratio
            if quality_metrics["total_pairs"] > 0:
                quality_metrics["average_length_ratio"] = total_length_ratio / quality_metrics["total_pairs"]
            
            # Calculate overall quality score
            issues_count = (quality_metrics["empty_translations"] + 
                          quality_metrics["identical_translations"] +
                          len(quality_metrics["suspicious_translations"]))
            quality_score = max(0.0, 1.0 - (issues_count / quality_metrics["total_pairs"]))
            quality_metrics["quality_score"] = quality_score
            
            return TaskResult.success_result(
                data=quality_metrics,
                metadata={"target_language": target_language}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="QUALITY_VALIDATION_FAILED",
                error_message=f"Translation quality validation failed: {str(e)}"
            )