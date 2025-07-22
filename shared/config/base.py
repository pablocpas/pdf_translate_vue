"""
Base configuration settings for PDF Translator.

This module consolidates all environment variable handling and configuration
that was previously scattered across multiple files.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This replaces the scattered environment variable access throughout
    the original codebase and provides type safety and validation.
    """
    
    # API Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", 
        env="OPENROUTER_BASE_URL"
    )
    
    # Model Configuration
    gpt_model: str = Field(default="gpt-4o-mini", env="GPT_MODEL")
    temperature: float = Field(default=0.3, env="TEMPERATURE")
    max_tokens: int = Field(default=4000, env="MAX_TOKENS")
    
    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://redis:6379/0", 
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://redis:6379/0", 
        env="CELERY_RESULT_BACKEND"
    )
    
    # Directory Configuration
    upload_folder: Path = Field(default=Path("/app/uploads"), env="UPLOAD_FOLDER")
    translated_folder: Path = Field(
        default=Path("/app/translated"), 
        env="TRANSLATED_FOLDER"
    )
    temp_folder: Path = Field(default=Path("/app/temp"), env="TEMP_FOLDER")
    
    # Processing Configuration
    dpi: int = Field(default=300, env="DPI")
    min_font_size: int = Field(default=8, env="MIN_FONT_SIZE")
    font_scale_factor: float = Field(default=0.8, env="FONT_SCALE_FACTOR")
    
    # Task Configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay_seconds: int = Field(default=5, env="RETRY_DELAY_SECONDS")
    task_timeout_seconds: int = Field(default=3600, env="TASK_TIMEOUT_SECONDS")
    
    # Development settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @field_validator("upload_folder", "translated_folder", "temp_folder", mode="before")
    @classmethod
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Ensure API key is provided."""
        if not v or v.strip() == "":
            raise ValueError("OpenAI API key is required")
        return v.strip()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    def ensure_directories(self) -> None:
        """
        Create required directories if they don't exist.
        
        This centralizes the directory creation logic that was duplicated
        across backend/main.py and worker/tasks.py.
        """
        for directory in [self.upload_folder, self.translated_folder, self.temp_folder]:
            directory.mkdir(parents=True, exist_ok=True)
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }