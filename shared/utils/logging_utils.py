"""
Logging configuration utilities.

This module provides centralized logging configuration to replace
the scattered logging setup throughout the original codebase.
"""

import logging
import sys
from typing import Optional
from ..config.environments import get_settings


def configure_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Log level (uses settings default if None)
        format_string: Log format string (uses default if None)
    """
    settings = get_settings()
    
    log_level = level or settings.log_level
    log_format = format_string or (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Set specific logger levels
    if not settings.debug:
        # Reduce verbosity of third-party libraries in production
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("celery").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)