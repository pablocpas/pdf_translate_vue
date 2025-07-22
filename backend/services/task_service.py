"""
Task management service.

This service handles Celery task operations, replacing the scattered
task management logic in the original backend.
"""

from typing import Optional, Dict, Any
from celery import Celery
from celery.result import AsyncResult

from shared.models.translation import TranslationTask, TranslationProgress
from shared.models.exceptions import ProcessingError
from shared.config.constants import TaskStatus
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TaskService:
    """
    Service for managing Celery tasks.
    
    This consolidates task status checking and management logic
    that was scattered across the original endpoints.
    """
    
    def __init__(self, celery_app: Celery):
        """
        Initialize the task service.
        
        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
    
    def get_task_status(self, task_id: str) -> TranslationTask:
        """
        Get the current status of a translation task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TranslationTask: Task status information
            
        Raises:
            ProcessingError: If task status cannot be retrieved
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            # Map Celery states to our task statuses
            status_mapping = {
                'PENDING': TaskStatus.PENDING,
                'STARTED': TaskStatus.PROCESSING,
                'SUCCESS': TaskStatus.COMPLETED,
                'FAILURE': TaskStatus.FAILED,
                'RETRY': TaskStatus.PROCESSING,
                'REVOKED': TaskStatus.FAILED
            }
            
            status = status_mapping.get(result.state, TaskStatus.PENDING)
            
            # Build base task info
            task = TranslationTask(
                id=task_id,
                status=status,
                original_file="",  # Would need to be stored separately
            )
            
            # Add additional info based on state
            if result.state == 'FAILURE':
                task.error = str(result.info) if result.info else "Unknown error"
                logger.error(f"Task {task_id} failed: {task.error}")
                
            elif result.state == 'SUCCESS':
                if isinstance(result.info, dict):
                    task.translated_file = result.info.get('translated_file')
                    logger.info(f"Task {task_id} completed successfully")
                    
            elif result.state in ['STARTED', 'RETRY']:
                # Check for progress information
                if isinstance(result.info, dict):
                    progress_info = result.info.get('progress', {})
                    if progress_info:
                        task.progress = TranslationProgress(
                            current=progress_info.get('current', 0),
                            total=progress_info.get('total', 1),
                            percent=progress_info.get('percent', 0)
                        )
            
            return task
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to get task status: {str(e)}",
                code="TASK_STATUS_FAILED",
                context={"task_id": task_id, "error": str(e)}
            )
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if task was cancelled successfully
            
        Raises:
            ProcessingError: If task cancellation fails
        """
        try:
            self.celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Task {task_id} cancelled")
            return True
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to cancel task: {str(e)}",
                code="TASK_CANCEL_FAILED",
                context={"task_id": task_id, "error": str(e)}
            )
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Optional[Dict[str, Any]]: Task result if available
            
        Raises:
            ProcessingError: If result retrieval fails
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            if result.state == 'SUCCESS':
                return result.info if isinstance(result.info, dict) else {}
            elif result.state == 'FAILURE':
                raise ProcessingError(
                    f"Task failed: {result.info}",
                    code="TASK_FAILED",
                    context={"task_id": task_id}
                )
            else:
                return None  # Task not completed yet
                
        except ProcessingError:
            raise  # Re-raise our custom exceptions
        except Exception as e:
            raise ProcessingError(
                f"Failed to get task result: {str(e)}",
                code="TASK_RESULT_FAILED",
                context={"task_id": task_id, "error": str(e)}
            )
    
    def is_task_completed(self, task_id: str) -> bool:
        """
        Check if a task has completed (successfully or with failure).
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if task is completed
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            return result.state in ['SUCCESS', 'FAILURE']
        except Exception:
            return False
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """
        Get information about currently active tasks.
        
        Returns:
            Dict[str, Any]: Active tasks information
        """
        try:
            inspect = self.celery_app.control.inspect()
            active = inspect.active()
            scheduled = inspect.scheduled()
            
            return {
                "active": active or {},
                "scheduled": scheduled or {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get active tasks: {str(e)}")
            return {"active": {}, "scheduled": {}}