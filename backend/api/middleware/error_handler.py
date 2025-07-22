"""
Global error handling middleware.

This module provides centralized error handling to replace the scattered
exception handling throughout the original codebase.
"""

from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from shared.models.exceptions import (
    PDFTranslatorError,
    ValidationError,
    FileError,
    ProcessingError,
    TranslationError,
    ConfigurationError
)
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_code: Internal error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        JSONResponse: Formatted error response
    """
    content = {
        "error": {
            "code": error_code,
            "message": message
        }
    }
    
    if details:
        content["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


async def pdf_translator_exception_handler(
    request: Request, 
    exc: PDFTranslatorError
) -> JSONResponse:
    """Handle custom PDFTranslatorError exceptions."""
    logger.error(
        f"PDFTranslatorError: {exc.code} - {str(exc)}",
        extra={"context": exc.context}
    )
    
    # Map exception types to HTTP status codes
    status_mapping = {
        ValidationError: status.HTTP_400_BAD_REQUEST,
        FileError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        TranslationError: status.HTTP_503_SERVICE_UNAVAILABLE,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_mapping.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return create_error_response(
        error_code=exc.code,
        message=str(exc),
        status_code=status_code,
        details=exc.context if exc.context else None
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return create_error_response(
        error_code="VALIDATION_ERROR",
        message="Invalid request data",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": exc.errors()}
    )


async def http_exception_handler(
    request: Request, 
    exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return create_error_response(
        error_code="HTTP_ERROR",
        message=exc.detail,
        status_code=exc.status_code
    )


async def general_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return create_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def add_exception_handlers(app: FastAPI) -> None:
    """
    Add all exception handlers to the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(PDFTranslatorError, pdf_translator_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)