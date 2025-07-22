"""
Language detection service.

This module provides language detection capabilities for source text analysis.
"""

from typing import List, Dict, Any
import re

from shared.models.task import TaskResult
from shared.utils.logging_utils import get_logger
from shared.config.constants import SUPPORTED_LANGUAGES

logger = get_logger(__name__)


class LanguageDetector:
    """
    Service for detecting the language of text samples.
    
    This class provides language detection functionality that can be
    extended with more sophisticated detection libraries if needed.
    """
    
    def __init__(self):
        """Initialize the language detector."""
        self._common_words = self._load_common_words()
    
    def detect_language(self, text_samples: List[str]) -> TaskResult:
        """
        Detect the language of text samples.
        
        This is a simplified implementation that could be enhanced
        with libraries like langdetect or polyglot.
        
        Args:
            text_samples: List of text samples for detection
            
        Returns:
            TaskResult: Detection result with language code
        """
        logger.debug(f"Detecting language from {len(text_samples)} text samples")
        
        try:
            if not text_samples:
                return TaskResult.error_result(
                    error_code="NO_TEXT_SAMPLES",
                    error_message="No text samples provided"
                )
            
            # Combine all text samples
            combined_text = " ".join(text_samples).lower()
            
            # Simple heuristic-based detection
            detection_result = self._detect_by_heuristics(combined_text)
            
            return TaskResult.success_result(
                data={
                    "detected_language": detection_result["language"],
                    "confidence": detection_result["confidence"],
                    "language_name": SUPPORTED_LANGUAGES.get(
                        detection_result["language"], 
                        "Unknown"
                    )
                },
                metadata={
                    "samples_analyzed": len(text_samples),
                    "total_characters": len(combined_text),
                    "method": "heuristic"
                }
            )
            
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="LANGUAGE_DETECTION_FAILED",
                error_message=f"Language detection failed: {str(e)}"
            )
    
    def _detect_by_heuristics(self, text: str) -> Dict[str, Any]:
        """
        Simple heuristic-based language detection.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict[str, Any]: Detection result with language and confidence
        """
        # Character-based patterns for common languages
        patterns = {
            'es': [
                r'\b(?:el|la|los|las|de|en|un|una|por|para|con|que|del)\b',
                r'[ñáéíóúü]',
                r'\b(?:español|castellano)\b'
            ],
            'en': [
                r'\b(?:the|and|of|in|to|a|is|it|you|that|he|was|for|on|are|as|with|his|they|i|at|be|this|have|from|or|one|had|by|word|but|not|what|all|were|we|when|your|can|said|there|use|an|each|which|she|do|how|their|if|will|up|other|about|out|many|then|them|these|so|some|her|would|make|like|into|him|has|two|more|go|no|way|could|my|than|first|been|call|who|its|now|find|long|down|day|did|get|come|made|may|part)\b'
            ],
            'fr': [
                r'\b(?:le|de|et|à|un|il|être|et|en|avoir|que|pour|dans|ce|son|une|sur|avec|ne|se|pas|tout|pouvoir|par|plus|dire|me|on|mon|lui|nous|comme|mais|son|elle|alors|même|temps|grand|petit|homme|femme|jour|année|pays|main|côté|où|moment|faire|voir|depuis|nouveau|devenir|premier|autre|chose|vie|monde|œil|air|eau|cœur|maison|partir|entre|deux|prendre|donner|falloir|porter|sans|contre)\b',
                r'[àâäéèêëïîôùûüÿç]'
            ],
            'de': [
                r'\b(?:der|die|und|in|den|von|zu|das|mit|sich|des|auf|für|ist|im|dem|nicht|ein|eine|als|auch|es|an|werden|aus|er|hat|daß|sie|nach|wird|bei|einer|um|am|sind|noch|wie|einem|über|einen|so|zum|war|haben|nur|oder|aber|vor|zur|bis|mehr|durch|man|sein|wurde|sei|in)\b',
                r'[äöüß]'
            ],
            'it': [
                r'\b(?:il|di|che|e|la|per|un|in|con|non|una|da|su|come|più|le|ma|se|nel|del|anche|lo|alla|tutto|questo|gli|tra|come|tutto|prima|molto|stesso|bene|dove|quando|perché|oggi|dopo|mentre|sopra|cosa|tempo|persona|anno|modo)\b',
                r'[àèìòù]'
            ],
            'pt': [
                r'\b(?:de|a|o|e|do|da|em|um|para|é|com|não|uma|os|no|se|na|por|mais|as|dos|como|mas|foi|ao|ele|das|tem|à|seu|sua|ou|ser|quando|muito|há|nos|já|está|eu|também|só|pelo|pela|até|isso|ela|entre|era|depois|sem|mesmo|aos|ter|seus|quem|nas|me|esse|eles|estão|você|tinha|foram|essa|num|nem|suas|meu|às|minha|têm|numa|pelos|elas|havia|seja|qual|será|nós|tenho|lhe|deles|essas|esses|pelas|este|fosse|dele|tu|te|vocês|vos|lhes|meus|minhas|teu|tua|teus|tuas|nosso|nossa|nossos|nossas|dela|delas|esta|estes|estas|aquele|aquela|aqueles|aquelas|isto|isso|aquilo|estou|está|estamos|estão|estive|esteve|estivemos|estiveram|estava|estávamos|estavam|estiver|estivesse|estivéssemos|estivessem|sou|é|somos|são|era|éramos|eram|fui|foi|fomos|foram|seja|sejamos|sejam|fosse|fôssemos|fossem|sendo|sido|tenho|tem|temos|têm|tinha|tínhamos|tinham|tive|teve|tivemos|tiveram|tenha|tenhamos|tenham|tivesse|tivéssemos|tivessem|tendo|tido)\b'
            ]
        }
        
        scores = {}
        
        for lang, lang_patterns in patterns.items():
            score = 0
            for pattern in lang_patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[lang] = score
        
        # Find language with highest score
        if scores:
            best_lang = max(scores, key=scores.get)
            max_score = scores[best_lang]
            
            # Calculate confidence based on score and text length
            confidence = min(0.95, max_score / (len(text.split()) + 1))
            
            # Minimum confidence threshold
            if confidence < 0.1:
                return {"language": "en", "confidence": 0.5}  # Default to English
            
            return {"language": best_lang, "confidence": confidence}
        
        # Fallback to English
        return {"language": "en", "confidence": 0.5}
    
    def _load_common_words(self) -> Dict[str, List[str]]:
        """
        Load common words for language detection.
        
        In a production system, this would load from external files.
        
        Returns:
            Dict[str, List[str]]: Common words by language
        """
        return {
            'en': ['the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i'],
            'es': ['el', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no'],
            'fr': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'],
            'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'],
            'it': ['il', 'di', 'che', 'e', 'la', 'per', 'un', 'in', 'con', 'non'],
            'pt': ['de', 'a', 'o', 'e', 'do', 'da', 'em', 'um', 'para', 'é']
        }
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.
        
        Returns:
            List[str]: Supported language codes
        """
        return list(SUPPORTED_LANGUAGES.keys())