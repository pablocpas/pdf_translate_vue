import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # --- Storage Provider Configuration ---
    STORAGE_PROVIDER: str = "minio"  # "minio" for local development, "s3" for production
    
    # --- Common S3/MinIO Configuration ---
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET: str
    AWS_REGION: str = 'us-east-1'
    AWS_S3_USE_SSL: bool = False
    
    # --- Environment-specific Endpoints ---
    # Internal endpoint (for operations like upload/download)
    AWS_S3_ENDPOINT_URL: str
    # Public endpoint (for presigned URLs accessible from frontend)
    AWS_S3_PUBLIC_ENDPOINT_URL: Optional[str] = None
    
    # --- Other Configuration ---
    TRANSLATED_TTL_DAYS: int = 7
    OPENAI_API_KEY: Optional[str] = None

settings = Settings()

# File paths (deprecated - will be replaced by S3)
PDF_INPUT_PATH = os.getenv('PDF_INPUT_PATH', 'original.pdf')
PDF_OUTPUT_PATH = os.getenv('PDF_OUTPUT_PATH', './output/translated_pdf.pdf')

ALLOWED_EXTENSIONS = {'pdf'}

OPENAI_API_KEY = settings.OPENAI_API_KEY

# GPT model configuration
GPT_MODEL = 'gpt-4o-mini'  # Make sure you have access to this model

# Other settings
MARGIN = 20
DEBUG_MODE = False

# Layout parser model configuration
MODEL_CONFIGS = {
    'primalayout': {
        'config_path': './models/primalayout/config.yaml',
        'model_path': './models/primalayout/model_final.pth'
    },
    'publaynet': {
        'config_path': './models/publaynet/config.yaml',
        'model_path': './models/publaynet/model_final.pth'
    }
}
# Original label maps for each model
ORIGINAL_LABEL_MAPS = {
    'primalayout': {
        1: "TextRegion",
        2: "ImageRegion",
        3: "TableRegion",
        4: "MathsRegion",
        5: "SeparatorRegion",
        6: "OtherRegion"
    },
    'publaynet': {
        0: "Text",
        1: "Title",
        2: "List",
        3: "Table",
        4: "Figure"
    }
}

# Normalized label maps that map to common types
LABEL_MAPS = {
    'primalayout': {
        1: "TextRegion",  # TextRegion -> TextRegion
        2: "ImageRegion", # ImageRegion -> ImageRegion
        3: "ImageRegion", # TableRegion -> ImageRegion
        4: "ImageRegion", # MathsRegion -> ImageRegion
        5: "ImageRegion", # SeparatorRegion -> ImageRegion
        6: "ImageRegion"  # OtherRegion -> ImageRegion
    },
    'publaynet': {
        0: "TextRegion", # Text -> TextRegion
        1: "TextRegion", # Title -> TextRegion
        2: "TextRegion", # List -> TextRegion
        3: "ImageRegion", # Table -> ImageRegion
        4: "ImageRegion"  # Figure -> ImageRegion
    }
}
EXTRA_CONFIG = ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.7]

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
