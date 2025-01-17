from openai import OpenAI
import logging
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

def translate_text(text: str, target_language: str) -> str:
    """
    Translates the text using OpenAI's GPT model.

    Args:
        text (str): Text to translate.
        target_language (str): Target language for translation.

    Returns:
        str: Translated text.
    """
    if not text.strip():
        return "No text to translate"

    # Convert ISO code to full language name
    language_name = LANGUAGE_MAP.get(target_language.lower(), target_language)
    
    prompt = (
        f"Act as an expert translator to {language_name}. "
        f"Your only task is to provide a direct translation of the given text. "
        f"Do not give explanations, additional comments, or summarize the content. "
        f"Do not add any preface or clarification, simply respond with the exact and complete translation. "
        f"If the text is already in {target_language}, simply return it as is.\n\n"
        f"Text to translate:\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        translated_text = response.choices[0].message.content.strip()
        logging.info("Text translated successfully.")
        return translated_text
    except Exception as e:
        logging.error(f"Error in OpenAI API: {e}")
        return text  # Return the original text in case of error
