from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, Document, ProcessingTask, TaskStatus
from app.core.security import get_password_hash, verify_password
from datetime import datetime
from typing import Optional
from app.db.models import TaskStatus, ProcessingTask

# User CRUD operations

async def create_user(db: AsyncSession, username: str, email: str, password: str,) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    db_user = User(username=username, email=email, hashed_password=hashed_password,)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


# Document CRUD operations

async def create_document(
    db: AsyncSession,
    user_id: int,
    filename: str,
    original_filename: str,
    file_path: str,
    file_size: int,
    mime_type: str
) -> Document:
    """Create a new document record"""
    db_document = Document(
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document


async def get_document(db: AsyncSession, document_id: int) -> Optional[Document]:
    """Get document by ID"""
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalars().first()


async def get_user_documents(db: AsyncSession, user_id: int):
    """Get all documents for a user"""
    result = await db.execute(select(Document).where(Document.user_id == user_id))
    return result.scalars().all()


# Task CRUD operations

async def create_task(
    db: AsyncSession,
    task_id: str,
    user_id: int,
    document_id: int,
    status: TaskStatus = TaskStatus.PENDING
) -> ProcessingTask:
    """Create a new processing task"""
    db_task = ProcessingTask(
        task_id=task_id,
        user_id=user_id,
        document_id=document_id,
        status=status
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


async def get_task(db: AsyncSession, task_id: str, user_id: int) -> Optional[ProcessingTask]:
    """Get task by task_id"""
    query = select(ProcessingTask).where(ProcessingTask.task_id == task_id)
    
    # Only filter by user_id if it is explicitly provided by the endpoint
    if user_id is not None:
        query = query.where(ProcessingTask.user_id == user_id)
        
    result = await db.execute(query)
    return result.scalars().first()


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: TaskStatus,
    result: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[ProcessingTask]:
    """Update task status and result"""
    db_task = await get_task(db, task_id)
    if not db_task:
        return None
    
    db_task.status = status
    if status == TaskStatus.PROCESSING and not db_task.started_at:
        db_task.started_at = datetime.timezone.utc.localize(datetime.datetime.now())
    elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        db_task.completed_at = datetime.timezone.utc.localize(datetime.datetime.now())
    
    if result:
        db_task.result = result
    if error_message:
        db_task.error_message = error_message
    
    await db.commit()
    await db.refresh(db_task)
    return db_task


async def get_user_tasks(db: AsyncSession, user_id: int):
    """Get all tasks for a user"""
    result = await db.execute(select(ProcessingTask).where(ProcessingTask.user_id == user_id))
    return result.scalars().all()
