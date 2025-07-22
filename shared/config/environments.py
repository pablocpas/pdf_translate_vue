"""
Environment-specific configuration management.

This module provides a singleton pattern for accessing application settings
and replaces the scattered configuration access throughout the codebase.
"""

from functools import lru_cache
from .base import Settings


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings instance.
    
    Uses LRU cache to ensure singleton behavior and avoid
    re-parsing environment variables on every call.
    
    Returns:
        Settings: The application settings instance
    """
    return Settings()


def ensure_required_directories() -> None:
    """
    Ensure all required directories exist.
    
    This is a convenience function that can be called during
    application startup to create necessary directories.
    """
    settings = get_settings()
    settings.ensure_directories()