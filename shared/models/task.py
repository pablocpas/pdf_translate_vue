"""
Task execution models.

This module defines models for task results and error handling,
replacing the inconsistent dictionary-based returns in the original code.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TaskError(BaseModel):
    """Structured error information for failed tasks."""
    code: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    traceback: Optional[str] = Field(None, description="Stack traceback for debugging")


class TaskResult(BaseModel):
    """
    Standard result format for all task operations.
    
    This provides a consistent return format that replaces the various
    dictionary formats used throughout the original codebase.
    """
    success: bool = Field(description="Whether the task succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[TaskError] = Field(None, description="Error information if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @classmethod
    def success_result(
        cls, 
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "TaskResult":
        """Create a successful task result."""
        return cls(
            success=True,
            data=data or {},
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(
        cls,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        traceback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "TaskResult":
        """Create a failed task result."""
        return cls(
            success=False,
            error=TaskError(
                code=error_code,
                message=error_message,
                details=error_details,
                traceback=traceback
            ),
            metadata=metadata or {}
        )