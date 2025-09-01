from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET: str
    AWS_S3_ENDPOINT_URL: str
    
    # Estas pueden tener valores por defecto razonables.
    AWS_REGION: str = 'us-east-1'
    AWS_S3_USE_SSL: bool = False
    TRANSLATED_TTL_DAYS: int = 7
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None

    AWS_S3_PUBLIC_ENDPOINT_URL: Optional[str] = None

settings = Settings()

# Configuration constants
MARGIN = 20
DEBUG_MODE = False

# Supported languages
SUPPORTED_LANGUAGES = {
    # European Languages
    'de': 'German',
    'ca': 'Catalan',
    'hr': 'Croatian',
    'da': 'Danish',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'es': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'nl': 'Dutch',
    'hu': 'Hungarian',
    'en': 'English',
    'it': 'Italian',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'sv': 'Swedish',
    'tr': 'Turkish',
    'gl': 'Galician',
    'eu': 'Basque',
    
    # Cyrillic Languages
    'ru': 'Russian',
    'uk': 'Ukrainian',
    'bg': 'Bulgarian',
    
    # East Asian Languages
    'zh': 'Chinese (Mandarin)',
    'ja': 'Japanese',
    'ko': 'Korean',
    
    # Other Scripts
    'ar': 'Arabic',
    'he': 'Hebrew',
    'el': 'Greek',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'th': 'Thai',
    'vi': 'Vietnamese'
}

# Default language (can be used as a fallback if needed)
DEFAULT_LANGUAGE = 'es'
