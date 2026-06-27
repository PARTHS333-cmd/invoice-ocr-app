from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
import os
import uuid
from app.db.database import get_db
from app.db.crud import (
    create_document,
    get_document,
    get_user_documents,
)
from app.core.security import get_current_active_user, get_current_user
from app.core.config import settings
from datetime import datetime
from fastapi.responses import FileResponse
from fastapi import status, Depends, HTTPException

from app.db.models import Document, User
router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload an invoice document"""
    user_id = current_user.id
    
    # Validate file size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed ({settings.max_upload_size} bytes)"
        )
    
    # Validate file type (simple check)
    allowed_types = ["image/jpeg", "image/png", "image/pdf", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Create upload directory if not exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Create document record in database
        db_document = await create_document(
            db,
            user_id=user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type
        )
        
        return db_document
    
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents for current user"""
    user_id = current_user.id
    documents = await get_user_documents(db, user_id)
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_info(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document info"""
    user_id = int(current_user["user_id"])
    document = await get_document(db, document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )
    
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download document file"""
    from fastapi.responses import FileResponse
    
    user_id = int(current_user["user_id"])
    document = await get_document(db, document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )
    
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    return FileResponse(
        document.file_path,
        filename=document.original_filename
    )
 # Ensure this CRUD function exists or write it below

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document record and its physical file from disk."""
    # 1. Fetch document metadata
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # 2. Security Check: Ensure this document belongs to the logged-in user
    if document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
        
    # 3. Delete physical file from your local uploads directory
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception:
            pass # Prevent DB desync if filesystem removal hits a temporary OS lock
            
    # 4. Remove database row tracking record
    await db.delete(document)
    await db.commit()
    
    return None
