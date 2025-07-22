"""
Application constants for PDF Translator.

This module centralizes all magic numbers and configuration constants
that were previously scattered throughout the codebase.
"""

from typing import Dict, List
from enum import Enum

# File processing constants
DEFAULT_DPI = 300
MIN_FONT_SIZE = 8
FONT_SCALE_FACTOR = 0.8
MAX_FILE_SIZE_MB = 50
SUPPORTED_FILE_EXTENSIONS = [".pdf"]

# Task and queue configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
TASK_TIMEOUT_SECONDS = 3600  # 1 hour

# Storage paths
UPLOADS_FOLDER = "uploads"
TRANSLATED_FOLDER = "translated"
TEMP_FOLDER = "temp"

# Language codes and names mapping
SUPPORTED_LANGUAGES: Dict[str, str] = {
    # European Languages
    "en": "English",
    "es": "Spanish", 
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "hu": "Hungarian",
    "cs": "Czech",
    "sk": "Slovak",
    "sl": "Slovenian",
    "hr": "Croatian",
    "bg": "Bulgarian",
    "ro": "Romanian",
    "el": "Greek",
    
    # Asian Languages
    "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "th": "Thai",
    "vi": "Vietnamese",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    
    # Middle Eastern and African Languages
    "ar": "Arabic",
    "he": "Hebrew",
    "fa": "Persian",
    "tr": "Turkish",
    "sw": "Swahili",
}

# Font mapping for different language families
FONT_MAPPING: Dict[str, str] = {
    # Latin-based languages use OpenSans
    "en": "OpenSans",
    "es": "OpenSans", 
    "fr": "OpenSans",
    "de": "OpenSans",
    "it": "OpenSans",
    "pt": "OpenSans",
    "nl": "OpenSans",
    "pl": "OpenSans",
    "ru": "OpenSans",
    "sv": "OpenSans",
    "da": "OpenSans",
    "no": "OpenSans",
    "fi": "OpenSans",
    "hu": "OpenSans",
    "cs": "OpenSans",
    "sk": "OpenSans",
    "sl": "OpenSans",
    "hr": "OpenSans",
    "bg": "OpenSans",
    "ro": "OpenSans",
    "el": "OpenSans",
    "tr": "OpenSans",
    "sw": "OpenSans",
    
    # CJK languages use specific fonts
    "zh": "STSong-Light",
    "zh-tw": "STSong-Light",
    "ja": "HeiseiMin-W3",
    "ko": "HYSMyeongJo-Medium",
    
    # Other languages with special requirements
    "th": "OpenSans",  # Could use Thai-specific font
    "vi": "OpenSans",
    "hi": "OpenSans",  # Could use Devanagari font
    "bn": "OpenSans",
    "ta": "OpenSans",
    "te": "OpenSans", 
    "ml": "OpenSans",
    "kn": "OpenSans",
    "gu": "OpenSans",
    "pa": "OpenSans",
    "ur": "OpenSans",
    "ar": "OpenSans",  # Could use Arabic font
    "he": "OpenSans",  # Could use Hebrew font
    "fa": "OpenSans",
}

class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ModelType(str, Enum):
    """Available translation model types."""
    PRIMALAYOUT = "primalayout"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"

# Translation API configuration
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS_PER_REQUEST = 4000
TEMPERATURE = 0.3