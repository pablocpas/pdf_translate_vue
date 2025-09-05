"""Módulo de Traducción de Texto.

Este archivo se encarga de la comunicación con la API de traducción
(OpenAI a través de OpenRouter). Proporciona una función asíncrona para
traducir lotes de texto, utilizando el formato de respuesta estructurada
para garantizar la fiabilidad de la salida.
"""
import json
import logging
from typing import List
from pydantic import BaseModel
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError
from ...infrastructure.config.settings import settings

# Cliente OpenAI configurado para OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENAI_API_KEY,
)

LANGUAGE_MAP = {
    'de': 'German', 'es-ct': 'Catalan', 'hr': 'Croatian', 'dk': 'Danish',
    'sk': 'Slovak', 'si': 'Slovenian', 'es': 'Spanish', 'fi': 'Finnish',
    'fr': 'French', 'nl': 'Dutch', 'hu': 'Hungarian', 'gb': 'English',
    'it': 'Italian', 'no': 'Norwegian', 'pl': 'Polish', 'pt': 'Portuguese',
    'ro': 'Romanian', 'se': 'Swedish', 'tr': 'Turkish', 'es-ga': 'Galician',
    'es-pv': 'Basque', 'ru': 'Russian', 'ua': 'Ukrainian', 'bg': 'Bulgarian',
    'cn': 'Chinese (Mandarin)', 'jp': 'Japanese', 'kr': 'Korean', 'arab': 'Arabic',
    'il': 'Hebrew', 'gr': 'Greek', 'in': 'Hindi', 'bd': 'Bengali',
    'lk': 'Tamil', 'th': 'Thai', 'vn': 'Vietnamese'
}

class TranslationResponse(BaseModel):
    """Define la estructura de respuesta esperada de la API de traducción."""
    translations: List[str]

async def translate_text_async(texts: List[str], target_language: str, language_model: str = "openai/gpt-4o-mini") -> List[str]:
    """Traduce una lista de textos de forma asíncrona al idioma especificado.

    Utiliza la funcionalidad de `parse` (Structured Outputs) del cliente de OpenAI
    para forzar al modelo a devolver un JSON que se ajuste al esquema `TranslationResponse`.
    Esto aumenta la robustez y evita errores de formato en la respuesta.

    :param texts: Una lista de cadenas de texto para traducir.
    :type texts: List[str]
    :param target_language: El código ISO del idioma de destino (ej. 'es', 'fr').
    :type target_language: str
    :param language_model: El identificador del modelo a utilizar (ej. 'openai/gpt-4o-mini').
    :type language_model: str
    :return: Una lista de los textos traducidos. En caso de error, devuelve la
             lista de textos originales como fallback.
    :rtype: List[str]
    :raises APIConnectionError, RateLimitError, APIStatusError: Si hay problemas de conexión con la API.
    """
    if not texts:
        return []

    language_name = LANGUAGE_MAP.get(target_language.lower(), target_language)
    system_prompt = (
        f"You are a professional translator. Translate each of the following texts into {language_name}. "
        "Preserve the original formatting and order. Return valid JSON with a 'translations' field, "
        "an array of strings that exactly matches the number of input texts."
    )
    user_prompt = (
        "Here is the list of texts in JSON. "
        "Return only the 'translations' in the same order:\n\n"
        f"{json.dumps(texts, ensure_ascii=False, indent=2)}"
    )

    try:
        response = await client.beta.chat.completions.parse(
            model=language_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=TranslationResponse,
            temperature=0
        )

        parsed_response = response.choices[0].message.parsed
        
        if len(parsed_response.translations) != len(texts):
            raise ValueError(f"La cantidad de traducciones ({len(parsed_response.translations)}) no coincide con los textos de entrada ({len(texts)}).")

        return parsed_response.translations

    except (APIConnectionError, RateLimitError, APIStatusError) as e:
        logging.error(f"Error de API al traducir: Código={e.status_code}, Respuesta={e.response.text}")
        raise e

    except Exception as e:
        logging.error(f"Error en traducción: {e}")
        return texts