from fastapi import FastAPI, UploadFile, HTTPException, Form, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import uuid
import os
import json
import logging
from pathlib import Path
from celery import Celery
from celery.result import AsyncResult
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Get directories from environment variables or use defaults
UPLOAD_DIR = Path(os.getenv('UPLOAD_FOLDER', '/app/uploads'))
TRANSLATED_DIR = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSLATED_DIR.mkdir(exist_ok=True)

logger.info(f"Upload directory: {UPLOAD_DIR}")
logger.info(f"Translated directory: {TRANSLATED_DIR}")

# Models and Enums
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
    progress: Optional[TranslationProgress] = None
    error: Optional[str] = None
    originalFile: str
    translatedFile: Optional[str] = None
    translationDataFile: Optional[str] = None



class Coordinates(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class Position(BaseModel):
    x: float
    y: float
    width: float
    height: float
    coordinates: Coordinates

class TextRegion(BaseModel):
    id: int
    original_text: str
    translated_text: str
    position: Position

class PageDimensions(BaseModel):
    width: float
    height: float

class PageData(BaseModel):
    text_regions: List[TextRegion]
    page_dimensions: PageDimensions

class TranslationData(BaseModel):
    pages: List[PageData]


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
async def upload_pdf(
    file: UploadFile = File(...), 
    target_language: str = Form("es"),
    model: str = Form("primalayout")
):
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Generate unique task ID
    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}.pdf"

    # Save the file on the server
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Send task to Celery worker with our custom task_id
    celery_task = celery_app.send_task(
        'translate_pdf',
        kwargs={
            'task_id': task_id,
            'pdf_path': str(file_path),
            'target_language': target_language,
            'model_type': model
        },
        task_id=task_id  # Use our UUID as the Celery task ID
    )

    logger.info(f"Task {task_id} sent for translation")
    return UploadResponse(taskId=task_id)


@app.get("/pdfs/status/{task_id}", response_model=TranslationTask)
async def get_translation_status(task_id: str):
    celery_task = AsyncResult(task_id, app=celery_app)

    if celery_task.state == 'PENDING':
        response = TranslationTask(
            id=task_id,
            status=TaskStatus.pending,
            originalFile=f"{task_id}.pdf",
            progress=TranslationProgress(
                current=0,
                total=0,
                percent=0
            )
        )
    elif celery_task.state == 'PROGRESS':
        meta = celery_task.info or {}
        response = TranslationTask(
            id=task_id,
            status=TaskStatus.processing,
            originalFile=f"{task_id}.pdf",
            progress=TranslationProgress(
                current=meta.get('current', 0),
                total=meta.get('total', 0),
                percent=meta.get('percent', 0)
            ) if meta else None
        )
    elif celery_task.state == 'SUCCESS':
        result = celery_task.result
        if result.get("status") == "failed":
            response = TranslationTask(
                id=task_id,
                status=TaskStatus.failed,
                originalFile=f"{task_id}.pdf",
                error=result.get("error", "Unknown error")
            )
        else:
            translated_file = result.get("output_path")
            if not translated_file:
                response = TranslationTask(
                    id=task_id,
                    status=TaskStatus.failed,
                    originalFile=f"{task_id}.pdf",
                    error="No output path returned from worker"
                )
            else:
                translation_data_path = result.get("translation_data_path")
                response = TranslationTask(
                    id=task_id,
                    status=TaskStatus.completed,
                    originalFile=f"{task_id}.pdf",
                    translatedFile=translated_file,
                    translationDataFile=translation_data_path if translation_data_path and Path(translation_data_path).exists() else None
                )
    elif celery_task.state == 'FAILURE':
        response = TranslationTask(
            id=task_id,
            status=TaskStatus.failed,
            originalFile=f"{task_id}.pdf",
            error=str(celery_task.result)
        )
    else:
        raise HTTPException(status_code=500, detail="Estado desconocido")
        
    return response

@app.get("/pdfs/download/original/{task_id}")
async def download_original_pdf(task_id: str):
    file_path = UPLOAD_DIR / f"{task_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")
    return FileResponse(file_path, media_type="application/pdf")

@app.get("/pdfs/download/translated/{task_id}")
async def download_translated_pdf(task_id: str):
    celery_task = AsyncResult(task_id, app=celery_app)

    if celery_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Translation is not complete")

    result = celery_task.result
    translated_file = result.get("output_path")
    if not translated_file or not Path(translated_file).exists():
        raise HTTPException(status_code=404, detail="Translated file not found")

    return FileResponse(translated_file, media_type="application/pdf")

@app.get("/pdfs/translation-data/{task_id}")
async def get_translation_data(task_id: str):
    try:
        logger.info(f"Getting translation data for task: {task_id}")
        celery_task = AsyncResult(task_id, app=celery_app)
        
        if celery_task.state != 'SUCCESS':
            logger.warning(f"Task {task_id} is not complete. State: {celery_task.state}")
            return JSONResponse(
                status_code=400,
                content={
                    "message": "Translation is not complete",
                    "code": "TRANSLATION_FAILED"
                }
            )
        
        result = celery_task.result
        logger.info(f"Task result: {result}")
        translation_data_path = result.get("translation_data_path")
        logger.info(f"Translation data path: {translation_data_path}")
        
        if not translation_data_path:
            logger.error(f"No translation data path found for task {task_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "message": "Translation data not found",
                    "code": "VALIDATION_ERROR"
                }
            )
        
        if not Path(translation_data_path).exists():
            logger.error(f"Translation data file not found at {translation_data_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "message": "Translation data file not found",
                    "code": "VALIDATION_ERROR"
                }
            )
        
        try:
            with open(translation_data_path, 'r', encoding='utf-8') as f:
                translation_data = json.load(f)
                logger.info(f"Successfully loaded translation data for task {task_id}")
                return JSONResponse(content=translation_data)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON for task {task_id}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "message": f"Error decoding JSON: {str(e)}",
                    "code": "VALIDATION_ERROR"
                }
            )
        except Exception as e:
            logger.error(f"Error reading translation data for task {task_id}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "message": f"Error reading translation data: {str(e)}",
                    "code": "SERVER_ERROR"
                }
            )
    except Exception as e:
        logger.error(f"Unexpected error in get_translation_data: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "message": "Error inesperado del servidor",
                "code": "SERVER_ERROR"
            }
        )

@app.put("/pdfs/translation-data/{task_id}")
async def update_translation_data(task_id: str, translation_data: TranslationData):
    celery_task = AsyncResult(task_id, app=celery_app)
    

    logger.info(f"Updating translation data for task: {task_id}")

    logger.info(f"LETS SEE THE DATA: {translation_data}")
    if celery_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Translation is not complete")
    
    result = celery_task.result
    translation_data_path = result.get("translation_data_path")
    
    if not translation_data_path or not Path(translation_data_path).exists():
        raise HTTPException(status_code=404, detail="Translation data not found")
    
    try:
        # Save updated translation data
        with open(translation_data_path, 'w', encoding='utf-8') as f:
            json.dump(jsonable_encoder(translation_data), f, ensure_ascii=False, indent=2)
            
        # Trigger PDF regeneration with updated data
        # TODO: Implement PDF regeneration with updated translation data
        
        return {"message": "Translation data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating translation data: {str(e)}")

@app.get("/")
async def read_root():
    return {"message": "PDF Translsfdfsdfator API"}
