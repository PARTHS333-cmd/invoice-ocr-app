import asyncio
from typing import Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory task storage
_tasks: Dict[str, Dict[str, Any]] = {}


class TaskManager:
    """In-memory task manager for tracking OCR processing tasks"""
    
    @staticmethod
    def create_task(task_id: str) -> Dict[str, Any]:
        """Create a new task"""
        task = {
            "task_id": task_id,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        _tasks[task_id] = task
        logger.info(f"Created task: {task_id}")
        return task
    
    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        return _tasks.get(task_id)
    
    @staticmethod
    def update_task(task_id: str, status: str, result: Optional[Any] = None, error: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update task status"""
        task = _tasks.get(task_id)
        if not task:
            return None
        
        task["status"] = status
        
        if status == "processing" and not task["started_at"]:
            task["started_at"] = datetime.utcnow().isoformat()
        
        if status in ["completed", "failed"]:
            task["completed_at"] = datetime.utcnow().isoformat()
        
        if result:
            task["result"] = result
        
        if error:
            task["error"] = error
        
        logger.info(f"Updated task {task_id}: status={status}")
        return task
    
    @staticmethod
    def delete_task(task_id: str) -> bool:
        """Delete task"""
        if task_id in _tasks:
            del _tasks[task_id]
            logger.info(f"Deleted task: {task_id}")
            return True
        return False
    
    @staticmethod
    def list_all_tasks() -> Dict[str, Dict[str, Any]]:
        """List all tasks (for debugging)"""
        return _tasks.copy()


# Create default instance
task_manager = TaskManager()
