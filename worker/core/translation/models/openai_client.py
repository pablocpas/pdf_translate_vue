"""
OpenAI/OpenRouter translation client.

This module provides a clean interface to OpenAI's translation API,
replacing the direct API calls scattered throughout the original code.
"""

import json
from typing import List
from openai import OpenAI
from pydantic import BaseModel

from shared.config import get_settings
from shared.models.task import TaskResult
from shared.models.exceptions import TranslationError
from shared.utils.logging_utils import get_logger
from shared.config.constants import SUPPORTED_LANGUAGES

logger = get_logger(__name__)


class TranslationResponse(BaseModel):
    """Structured response model for OpenAI translation."""
    translations: List[str]


class OpenAITranslationClient:
    """
    Client for OpenAI/OpenRouter translation services.
    
    This class encapsulates all OpenAI API interactions that were
    scattered throughout the original translator code.
    """
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.settings = get_settings()
        self.client = self._create_client()
    
    def _create_client(self) -> OpenAI:
        """
        Create and configure OpenAI client.
        
        Returns:
            OpenAI: Configured OpenAI client
        """
        return OpenAI(
            base_url=self.settings.openrouter_base_url,
            api_key=self.settings.openai_api_key,
        )
    
    def translate_texts(
        self,
        texts: List[str],
        target_language: str,
        model: str = None
    ) -> TaskResult:
        """
        Translate a list of texts using OpenAI API.
        
        This method replaces the complex translation logic in the
        original translator.py file.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            model: Model to use (optional)
            
        Returns:
            TaskResult: Translation result
        """
        logger.debug(f"Translating {len(texts)} texts to {target_language}")
        
        try:
            # Validate inputs
            if not texts:
                return TaskResult.success_result(
                    data={"translations": []},
                    metadata={"message": "No texts to translate"}
                )
            
            # Get target language name
            target_lang_name = SUPPORTED_LANGUAGES.get(
                target_language.lower(), 
                target_language.title()
            )
            
            # Prepare translation prompt
            prompt = self._build_translation_prompt(texts, target_lang_name)
            
            # Make API call
            api_result = self._call_translation_api(prompt, model)
            if not api_result.success:
                return api_result
            
            # Parse response
            translations = api_result.data["translations"]
            
            # Validate translation count
            if len(translations) != len(texts):
                logger.warning(
                    f"Translation count mismatch: expected {len(texts)}, got {len(translations)}"
                )
                # Pad with original texts if needed
                while len(translations) < len(texts):
                    translations.append(texts[len(translations)])
            
            return TaskResult.success_result(
                data={"translations": translations[:len(texts)]},
                metadata={
                    "target_language": target_language,
                    "model": model or self.settings.gpt_model,
                    "original_count": len(texts)
                }
            )
            
        except Exception as e:
            logger.error(f"Translation API call failed: {str(e)}", exc_info=True)
            return TaskResult.error_result(
                error_code="TRANSLATION_API_FAILED",
                error_message=f"Translation API call failed: {str(e)}",
                traceback=str(e)
            )
    
    def _build_translation_prompt(self, texts: List[str], target_language: str) -> str:
        """
        Build the translation prompt for the API.
        
        Args:
            texts: List of texts to translate
            target_language: Target language name
            
        Returns:
            str: Formatted prompt
        """
        # Create numbered list of texts
        texts_list = "\n".join(f"{i+1}. {text}" for i, text in enumerate(texts))
        
        prompt = f"""Translate the following texts to {target_language}. 
Maintain the original meaning and context. If a text cannot be translated, return it unchanged.

Texts to translate:
{texts_list}

Provide the translations in the same order, maintaining the exact same number of translations as input texts."""
        
        return prompt
    
    def _call_translation_api(
        self, 
        prompt: str, 
        model: str = None
    ) -> TaskResult:
        """
        Make the actual API call to OpenAI.
        
        Args:
            prompt: Translation prompt
            model: Model to use
            
        Returns:
            TaskResult: API call result
        """
        try:
            translation_model = model or self.settings.gpt_model
            
            # Make API call with structured output
            response = self.client.beta.chat.completions.parse(
                model=translation_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the given texts accurately while preserving context and meaning."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format=TranslationResponse,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens
            )
            
            # Parse structured response
            translation_response = response.choices[0].message.parsed
            
            if not translation_response or not translation_response.translations:
                return TaskResult.error_result(
                    error_code="EMPTY_TRANSLATION_RESPONSE",
                    error_message="API returned empty translation response"
                )
            
            logger.debug(f"API returned {len(translation_response.translations)} translations")
            return TaskResult.success_result(
                data={"translations": translation_response.translations},
                metadata={"model": translation_model}
            )
            
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"OpenAI API call failed: {str(e)}", exc_info=True)
            
            # Check for specific API errors
            error_message = str(e)
            if "rate_limit" in error_message.lower():
                error_code = "RATE_LIMIT_EXCEEDED"
            elif "invalid_api_key" in error_message.lower():
                error_code = "INVALID_API_KEY"
            elif "model_not_found" in error_message.lower():
                error_code = "MODEL_NOT_FOUND"
            else:
                error_code = "API_CALL_FAILED"
            
            return TaskResult.error_result(
                error_code=error_code,
                error_message=f"OpenAI API call failed: {error_message}",
                traceback=str(e)
            )
    
    def test_connection(self) -> TaskResult:
        """
        Test the connection to OpenAI API.
        
        Returns:
            TaskResult: Connection test result
        """
        try:
            # Simple test translation
            test_result = self.translate_texts(
                texts=["Hello, world!"],
                target_language="es",
                model=self.settings.gpt_model
            )
            
            if test_result.success:
                return TaskResult.success_result(
                    data={"status": "connected"},
                    metadata={"test_translation": test_result.data["translations"][0]}
                )
            else:
                return test_result
                
        except Exception as e:
            return TaskResult.error_result(
                error_code="CONNECTION_TEST_FAILED",
                error_message=f"Connection test failed: {str(e)}"
            )
    
    def get_available_models(self) -> TaskResult:
        """
        Get list of available models.
        
        Returns:
            TaskResult: Available models information
        """
        try:
            # This is a simplified version - in practice you'd call the models endpoint
            available_models = [
                "gpt-4o",
                "gpt-4o-mini", 
                "gpt-3.5-turbo"
            ]
            
            return TaskResult.success_result(
                data={"models": available_models},
                metadata={"default_model": self.settings.gpt_model}
            )
            
        except Exception as e:
            return TaskResult.error_result(
                error_code="MODELS_FETCH_FAILED",
                error_message=f"Failed to fetch available models: {str(e)}"
            )