import json
import logging
from typing import List
from pydantic import BaseModel
from openai import OpenAI
from ...infrastructure.config.settings import GPT_MODEL, OPENAI_API_KEY

# Configura el cliente con tu base_url y API Key de OpenRouter o OpenAI:
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# Mapeo ISO -> nombre de idioma
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

# Clase Pydantic que define la estructura de la respuesta
class TranslationResponse(BaseModel):
    translations: List[str]

def translate_text(texts: List[str], target_language: str) -> List[str]:
    """
    Translates a list of texts into the specified language using
    OpenAI's Structured Outputs feature. It ensures the model
    returns valid JSON that matches the TranslationResponse schema.

    Args:
        texts (List[str]): List of texts to translate.
        target_language (str): Target language ISO code (e.g. 'es', 'en').

    Returns:
        List[str]: The translated texts in the same order.
    """
    # Si la lista está vacía, devolverla tal cual:
    if not texts:
        return []

    # Convertimos el código ISO a nombre de idioma (o usamos el código si no está en el dict).
    language_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    # Mensaje system que indica al modelo qué hacer y cómo formatear la salida.
    system_prompt = (
        f"You are a professional translator. Translate each of the following texts into {language_name}. "
        "Preserve the original formatting and order. Return valid JSON with a 'translations' field, "
        "an array of strings that exactly matches the number of input texts."
    )

    # Mensaje user que incluye la lista de textos en JSON.
    user_prompt = (
        "Here is the list of texts in JSON. "
        "Return only the 'translations' in the same order:\n\n"
        f"{json.dumps(texts, ensure_ascii=False, indent=2)}"
    )

    try:
        # Llamada con response_format para forzar la estructura devuelta.
        response = client.beta.chat.completions.parse(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=TranslationResponse,
            temperature=0
        )

        # Extraemos la respuesta parseada como instancia de TranslationResponse.
        parsed_response = response.choices[0].message.parsed
        
        # Validamos que la longitud de las traducciones coincida con los textos de entrada.
        if len(parsed_response.translations) != len(texts):
            raise ValueError(
                f"Number of translations ({len(parsed_response.translations)}) "
                f"does not match input texts ({len(texts)})."
            )

        return parsed_response.translations

    except Exception as e:
        logging.error(f"Translation error: {e}")
        # Fallback: devolver los textos originales en caso de fallo.
        return texts
