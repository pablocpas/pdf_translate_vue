from openai import OpenAI
import logging
from pydantic import BaseModel
from typing import List
from ...infrastructure.config.settings import GPT_MODEL, OPENAI_API_KEY

client = OpenAI()

# Map ISO language codes to full names
LANGUAGE_MAP = {
    'es': 'Spanish',
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese'
}

class TranslationResponse(BaseModel):
    translations: List[str]

def translate_text(texts: List[str], target_language: str) -> List[str]:
    """
    Translates texts using OpenAI's GPT model with structured output.

    Args:
        texts (list[str]): List of texts to translate.
        target_language (str): Target language ISO code.

    Returns:
        list[str]: Translated texts in the same order.
    """
    if not texts:
        return []

    language_name = LANGUAGE_MAP.get(target_language.lower(), target_language)
    
    response = client.beta.chat.completions.parse(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": f"Translate these texts to {language_name} exactly as they appear, without adding any numbers or prefixes. Maintain the original formatting and order."},
            {"role": "user", "content": "Texts to translate:\n" + "\n---\n".join(texts)}
        ],
        response_format=TranslationResponse,
        temperature=0
    )
    
    try:
        parsed_response = response.choices[0].message.parsed
        if len(parsed_response.translations) != len(texts):
            raise ValueError("Translations count mismatch")
            
        return parsed_response.translations
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return [text for text in texts]  # Fallback returning original texts
