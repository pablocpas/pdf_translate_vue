from fastapi import FastAPI, UploadFile, HTTPException, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from enum import Enum
from typing import Optional
import uuid
import os
import logging
from pathlib import Path
from celery import Celery
from celery.result import AsyncResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Crear directorios para almacenar archivos
UPLOAD_DIR = Path("uploads")
TRANSLATED_DIR = Path("translated")
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSLATED_DIR.mkdir(exist_ok=True)

# Modelos y enumeraciones
class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class TranslationProgress(BaseModel):
    current: int = 0
    total: int = 0
    percent: int = 0

class TranslationTask(BaseModel):
    id: str
    status: TaskStatus
    originalFile: str
    translatedFile: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[TranslationProgress] = None

class UploadResponse(BaseModel):
    taskId: str

# Instancia de FastAPI
app = FastAPI(title="PDF Translator API")

# Configurar CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/pdfs/translate", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), target_language: str = Form("es")):
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    # Generar ID único para la tarea
    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}.pdf"

    # Guardar archivo en el servidor
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Enviar tarea al worker de Celery
    celery_task = celery_app.send_task(
        'translate_pdf',
        args=[task_id, str(file_path), target_language]
    )

    logger.info(f"Tarea {task_id} enviada para traducción")
    return UploadResponse(taskId=celery_task.id)

@app.get("/pdfs/status/{task_id}", response_model=TranslationTask)
async def get_translation_status(task_id: str):
    celery_task = AsyncResult(task_id, app=celery_app)

    # Mapear el estado de Celery a los estados definidos en la API
    if celery_task.state == 'PENDING':
        return TranslationTask(
            id=task_id,
            status=TaskStatus.pending,
            originalFile=f"uploads/{task_id}.pdf"
        )
    elif celery_task.state == 'PROGRESS':
        meta = celery_task.info or {}
        logger.info(f"Progress meta: {meta}")  # Mejor logging
        return TranslationTask(
            id=task_id,
            status=TaskStatus.processing,
            originalFile=f"uploads/{task_id}.pdf",
            progress=TranslationProgress(
                current=meta.get('current', 0),
                total=meta.get('total', 0),
                percent=meta.get('percent', 0)
            ) if meta else None
        )
    elif celery_task.state == 'SUCCESS':
        result = celery_task.result
        return TranslationTask(
            id=task_id,
            status=TaskStatus.completed,
            originalFile=f"uploads/{task_id}.pdf",
            translatedFile=result.get("translated_file", "")
        )
    elif celery_task.state == 'FAILURE':
        return TranslationTask(
            id=task_id,
            status=TaskStatus.failed,
            originalFile=f"uploads/{task_id}.pdf",
            error=str(celery_task.result)
        )
    else:
        raise HTTPException(status_code=500, detail="Estado desconocido")

@app.get("/pdfs/download/{task_id}")
async def download_translated_pdf(task_id: str):
    celery_task = AsyncResult(task_id, app=celery_app)

    if celery_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="La traducción no está completa")

    result = celery_task.result
    translated_file = result.get("translated_file")
    if not translated_file or not Path(translated_file).exists():
        raise HTTPException(status_code=404, detail="Archivo traducido no encontrado")

    return FileResponse(translated_file, media_type="application/pdf")

@app.get("/")
async def read_root():
    return {"message": "PDF Translator API"}
