import os

# File paths
PDF_INPUT_PATH = os.getenv('PDF_INPUT_PATH', 'original.pdf')
PDF_OUTPUT_PATH = os.getenv('PDF_OUTPUT_PATH', './output/translated_pdf.pdf')

ALLOWED_EXTENSIONS = {'pdf'}

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# GPT model configuration
GPT_MODEL = 'gpt-4o-mini'  # Make sure you have access to this model

# Other settings
MARGIN = 20
DEBUG_MODE = False

# Layout parser model configuration
MODEL_CONFIG_PATH = './models/config.yaml'
MODEL_PATH = './models/model_final.pth'
LABEL_MAP = {
    1: "TextRegion",
    2: "ImageRegion",
    3: "TableRegion",
    4: "MathsRegion",
    5: "SeparatorRegion",
    6: "OtherRegion"
}
EXTRA_CONFIG = ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.7]

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Supported languages
SUPPORTED_LANGUAGES = {
    'es': 'Spanish',
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    # Add more languages as needed
}

# Default language (can be used as a fallback if needed)
DEFAULT_LANGUAGE = 'es'
