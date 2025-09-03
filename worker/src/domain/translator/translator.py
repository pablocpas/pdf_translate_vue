import json
import logging
from typing import List
from pydantic import BaseModel
from openai import AsyncOpenAI
from ...infrastructure.config.settings import settings
from openai import APIConnectionError, RateLimitError, APIStatusError

# Cliente OpenAI configurado para OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENAI_API_KEY,
)

# Mapeo de códigos ISO a nombres de idiomas
LANGUAGE_MAP = {
    'de': 'German',
    'es-ct': 'Catalan',
    'hr': 'Croatian',
    'dk': 'Danish',
    'sk': 'Slovak',
    'si': 'Slovenian',
    'es': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'nl': 'Dutch',
    'hu': 'Hungarian',
    'gb': 'English',
    'it': 'Italian',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'se': 'Swedish',
    'tr': 'Turkish',
    'es-ga': 'Galician',
    'es-pv': 'Basque',
    'ru': 'Russian',
    'ua': 'Ukrainian',
    'bg': 'Bulgarian',
    'cn': 'Chinese (Mandarin)',
    'jp': 'Japanese',
    'kr': 'Korean',
    'arab': 'Arabic',
    'il': 'Hebrew',
    'gr': 'Greek',
    'in': 'Hindi',
    'bd': 'Bengali',
    'lk': 'Tamil',
    'th': 'Thai',
    'vn': 'Vietnamese'
}

# Estructura de respuesta para las traducciones
class TranslationResponse(BaseModel):
    translations: List[str]

async def translate_text_async(texts: List[str], target_language: str, language_model: str = "openai/gpt-4o-mini") -> List[str]:
    """
    Traduce una lista de textos al idioma especificado usando Structured Outputs de OpenAI.
    Garantiza que el modelo devuelva JSON válido que coincida con el esquema TranslationResponse.

    Args:
        texts: Lista de textos a traducir
        target_language: Código ISO del idioma destino (ej. 'es', 'en')
        language_model: Modelo a usar para la traducción

    Returns:
        Lista de textos traducidos en el mismo orden
    """
    # Retornar lista vacía si no hay textos
    if not texts:
        return []

    # Convertir código ISO a nombre de idioma
    language_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    # Prompt del sistema para el modelo
    system_prompt = (
        f"You are a professional translator. Translate each of the following texts into {language_name}. "
        "Preserve the original formatting and order. Return valid JSON with a 'translations' field, "
        "an array of strings that exactly matches the number of input texts."
    )

    # Prompt del usuario con los textos a traducir
    user_prompt = (
        "Here is the list of texts in JSON. "
        "Return only the 'translations' in the same order:\n\n"
        f"{json.dumps(texts, ensure_ascii=False, indent=2)}"
    )

    try:
        # Llamada con formato de respuesta estructurado
        response = await client.beta.chat.completions.parse(
            model=language_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=TranslationResponse,
            temperature=0
        )

        # Extraer respuesta parseada
        parsed_response = response.choices[0].message.parsed
        
        # Validar longitud de traducciones
        if len(parsed_response.translations) != len(texts):
            raise ValueError(
                f"Number of translations ({len(parsed_response.translations)}) "
                f"does not match input texts ({len(texts)})."
            )

        return parsed_response.translations


    except (APIConnectionError, RateLimitError, APIStatusError) as e:
            logging.error(f"Error de API al traducir: Código={e.status_code}, Respuesta={e.response.text}")
            raise e  # Relanzar la excepción


    except Exception as e:
        logging.error(f"Error en traducción: {e}")
        # Fallback: devolver textos originales
        return texts
