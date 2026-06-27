"""Task status polling and WebSocket routes."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.db.models import User
from app.db import crud
from app.services.task_manager import task_manager

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    stage: str
    document_id: int
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    task = task_manager.get_task(task_id)
    if not task:
        db_task = await crud.get_task(db, task_id, current_user.id)
        if not db_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return TaskStatusResponse(
            task_id=db_task.task_id,
            status=db_task.status,
            progress=db_task.progress,
            stage=db_task.stage or "",
            document_id=db_task.document_id,
            result=db_task.result,
            error=db_task.error_message,
            created_at=db_task.created_at.isoformat() if db_task.created_at else "",
            completed_at=db_task.completed_at.isoformat() if db_task.completed_at else None
        )
    
    if task["owner_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return TaskStatusResponse(**task)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket
    
    def disconnect(self, task_id: str):
        self.active_connections.pop(task_id, None)
    
    async def send_progress(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(data)
            except Exception:
                self.disconnect(task_id)


manager = ConnectionManager()


@router.websocket("/ws/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str, token: str):
    from jose import jwt, JWTError
    from app.core.config import get_settings
    
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return
    await websocket.accept()

    await task_manager.connect(task_id, websocket)

    try:
        while True:
            # This listens for any disconnect signals from the browser frontend
            await websocket.receive_text()
    except Exception:
        # 4. Clean up the connection if the user closes the page or disconnects
        if hasattr(task_manager, 'disconnect'):
            await task_manager.disconnect(task_id, websocket)
    
    async def on_task_update(task_data: dict):
        await manager.send_progress(task_id, {
            "type": "progress",
            "task_id": task_id,
            "progress": task_data.get("progress", 0),
            "stage": task_data.get("stage", ""),
            "status": task_data.get("status", "unknown")
        })
        if task_data.get("status") == "completed" and task_data.get("result"):
            await manager.send_progress(task_id, {
                "type": "complete",
                "task_id": task_id,
                "result": task_data["result"]
            })
        if task_data.get("status") == "failed":
            await manager.send_progress(task_id, {
                "type": "error",
                "task_id": task_id,
                "error": task_data.get("error", "Unknown error")
            })
    
    task_manager.register_callback(websocket, task_id)
    
    task = task_manager.get_task(task_id)
    if task:
        await websocket.send_json({
            "type": "progress",
            "task_id": task_id,
            "progress": task.get("progress", 0),
            "stage": task.get("stage", ""),
            "status": task.get("status", "unknown")
        })
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(task_id)
    except Exception:
        manager.disconnect(task_id)