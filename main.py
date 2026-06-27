"""Invoice OCR Processor - Main FastAPI Application."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.api import auth_router, documents_router, tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started")
    yield
    print("👋 Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Privacy-focused local invoice processing with PaddleOCR",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )