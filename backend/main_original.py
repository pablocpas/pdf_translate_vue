from fastapi import FastAPI, UploadFile, HTTPException, Form, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Any
import uuid
import os
import json
import logging
from pathlib import Path
from celery import Celery
from celery.result import AsyncResult
from fastapi.encoders import jsonable_encoder

# --- Configuración (Sin cambios) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

UPLOAD_DIR = Path(os.getenv('UPLOAD_FOLDER', '/app/uploads'))
TRANSLATED_DIR = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSLATED_DIR.mkdir(exist_ok=True)

logger.info(f"Upload directory: {UPLOAD_DIR}")
logger.info(f"Translated directory: {TRANSLATED_DIR}")

# --- Modelos Pydantic (Ajustados) ---

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingStep(str, Enum):
    QUEUED = "En cola"
    CONVERTING_PDF = "Convirtiendo PDF a imágenes"
    PROCESSING_PAGES = "Procesando páginas en paralelo"
    COMBINING_PDF = "Ensamblando PDF final"
    UNKNOWN = "Desconocido"

class TranslationProgress(BaseModel):
    step: ProcessingStep = ProcessingStep.QUEUED
    details: Optional[Any] = None # Para info como "Página 5 de 10"

class TranslationTask(BaseModel):
    id: str
    status: TaskStatus
    progress: Optional[TranslationProgress] = None
    error: Optional[str] = None
    originalFile: str
    translatedFile: Optional[str] = None
    # El `translationDataFile` se obtiene de un endpoint dedicado, no se expone aquí directamente.

class UploadResponse(BaseModel):
    taskId: str

# El resto de modelos de datos (TranslationData, PagePositionData, etc.) se mantienen igual.
class TranslationText(BaseModel):
    id: int
    original_text: str
    translated_text: str

class PageTranslation(BaseModel):
    page_number: int
    translations: List[TranslationText]

class TranslationData(BaseModel):
    pages: List[PageTranslation]


# --- Instancia de FastAPI (Sin cambios) ---
app = FastAPI(title="PDF Translator API - Parallel Worker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- HELPERS ---
def get_final_task_result(task_id: str) -> Optional[AsyncResult]:
    """
    Sigue la cadena de tareas desde la orquestadora hasta la finalizadora.
    """
    orchestrator_task = AsyncResult(task_id, app=celery_app)
    
    # Si la tarea orquestadora falló, no hay nada más que hacer.
    if orchestrator_task.state == 'FAILURE':
        return orchestrator_task

    # Si la orquestadora tuvo éxito, su resultado contiene el ID de la tarea de combinación.
    if orchestrator_task.state == 'SUCCESS':
        result = orchestrator_task.result
        if isinstance(result, dict) and result.get('result_task_id'):
            final_task_id = result['result_task_id']
            return AsyncResult(final_task_id, app=celery_app)
    
    # Si la orquestadora está en progreso o pendiente, devolvemos su estado.
    return orchestrator_task


# --- Endpoints (Modificados) ---

@app.post("/pdfs/translate", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...), 
    target_language: str = Form("es"),
    model: str = Form("primalayout")
):
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}.pdf"

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # La tarea `translate_pdf` ahora es la orquestadora.
    # El ID de la tarea que contiene el resultado final se devolverá en el `result` de esta.
    celery_app.send_task(
        'translate_pdf',
        kwargs={
            'pdf_path': str(file_path),
            'task_id': task_id, # Pasamos el ID para nombrar archivos
            'target_language': target_language,
            'model_type': model
        },
        task_id=task_id  # Este es el ID de la tarea orquestadora
    )

    logger.info(f"Task {task_id} sent for translation orchestration.")
    return UploadResponse(taskId=task_id)


@app.get("/pdfs/status/{task_id}", response_model=TranslationTask)
async def get_translation_status(task_id: str):
    """
    Endpoint de estado inteligente que sigue la cadena de tareas.
    """
    orchestrator_task = AsyncResult(task_id, app=celery_app)
    
    response_data = {
        "id": task_id,
        "originalFile": f"{task_id}.pdf"
    }

    if orchestrator_task.state == 'PENDING':
        response_data["status"] = TaskStatus.PENDING
        response_data["progress"] = TranslationProgress(step=ProcessingStep.QUEUED)

    elif orchestrator_task.state == 'PROGRESS':
        response_data["status"] = TaskStatus.PROCESSING
        meta = orchestrator_task.info or {}
        response_data["progress"] = TranslationProgress(
            step=ProcessingStep.CONVERTING_PDF,
            details=meta.get('status')
        )
    
    elif orchestrator_task.state == 'FAILURE':
        response_data["status"] = TaskStatus.FAILED
        response_data["error"] = str(orchestrator_task.result)

    elif orchestrator_task.state == 'SUCCESS':
        # La orquestadora ha terminado, ahora miramos la tarea de combinación.
        result = orchestrator_task.result
        final_task_id = result.get('result_task_id') if isinstance(result, dict) else None
        if not final_task_id:
            response_data["status"] = TaskStatus.FAILED
            response_data["error"] = "Orchestrator task succeeded but did not return a result task ID."
        else:
            final_task = AsyncResult(final_task_id, app=celery_app)
            
            if final_task.state == 'PENDING':
                 response_data["status"] = TaskStatus.PROCESSING
                 response_data["progress"] = TranslationProgress(step=ProcessingStep.PROCESSING_PAGES)
            
            elif final_task.state == 'PROGRESS':
                response_data["status"] = TaskStatus.PROCESSING
                meta = final_task.info or {}
                response_data["progress"] = TranslationProgress(
                    step=ProcessingStep.COMBINING_PDF,
                    details=meta.get('status')
                )

            elif final_task.state == 'FAILURE':
                response_data["status"] = TaskStatus.FAILED
                response_data["error"] = str(final_task.result)
            
            elif final_task.state == 'SUCCESS':
                result = final_task.result
                if isinstance(result, dict) and result.get("status") == "failed":
                    response_data["status"] = TaskStatus.FAILED
                    response_data["error"] = result.get("error", "Unknown error during finalization.")
                else:
                    response_data["status"] = TaskStatus.COMPLETED
                    if isinstance(result, dict) and result.get("output_path"):
                        response_data["translatedFile"] = result.get("output_path")
            else: # Otros estados como RETRY
                response_data["status"] = TaskStatus.PROCESSING
                response_data["progress"] = TranslationProgress(step=ProcessingStep.UNKNOWN, details=f"Final task state: {final_task.state}")
    
    else: # Otros estados como RETRY
        response_data["status"] = TaskStatus.PROCESSING
        response_data["progress"] = TranslationProgress(step=ProcessingStep.UNKNOWN, details=f"Orchestrator task state: {orchestrator_task.state}")

    return TranslationTask(**response_data)


@app.get("/pdfs/download/translated/{task_id}")
async def download_translated_pdf(task_id: str):
    final_task = get_final_task_result(task_id)

    if not final_task or final_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Translation is not complete or has failed.")

    result = final_task.result
    if not isinstance(result, dict):
        raise HTTPException(status_code=400, detail="Invalid task result format.")
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=f"Translation failed: {result.get('error')}")

    translated_file = result.get("output_path")
    if not translated_file or not Path(translated_file).exists():
        raise HTTPException(status_code=404, detail="Translated file not found.")

    return FileResponse(
        translated_file,
        media_type="application/pdf",
        filename=f"{task_id}_translated.pdf",
        headers={
            "Content-Disposition": 'inline; filename="translated.pdf"'
        }
    )


@app.get("/pdfs/translation-data/{task_id}")
async def get_translation_data(task_id: str):
    # La lógica para encontrar el archivo de datos es la misma que para el PDF
    # Se basa en el nombre de archivo del PDF traducido.
    final_task = get_final_task_result(task_id)

    if not final_task or final_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Translation is not complete or has failed.")

    result = final_task.result
    if not isinstance(result, dict):
        raise HTTPException(status_code=400, detail="Invalid task result format.")
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=f"Translation failed: {result.get('error')}")

    translated_pdf_path = result.get("output_path")
    if not translated_pdf_path:
        raise HTTPException(status_code=404, detail="Translated PDF path not found in result.")

    # Los nombres de los archivos de datos se derivan del nombre del PDF de salida
    base_path = translated_pdf_path.replace('.pdf', '')
    translation_data_path = f"{base_path}_translation_data.json"
    position_data_path = f"{base_path}_translation_data_position.json"
    
    if not Path(translation_data_path).exists() or not Path(position_data_path).exists():
        raise HTTPException(status_code=404, detail="Translation or position data files not found.")
        
    with open(translation_data_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
    with open(position_data_path, 'r', encoding='utf-8') as f:
        positions = json.load(f)

    return JSONResponse(content={"pages": translations["pages"], "positions": positions})


@app.put("/pdfs/translation-data/{task_id}")
async def update_translation_data(task_id: str, translation_data: TranslationData):
    # Esta lógica no necesita cambiar mucho, pero debe asegurarse de que la tarea original haya terminado.
    final_task = get_final_task_result(task_id)
    if not final_task or final_task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Original translation is not complete.")

    result = final_task.result
    if not isinstance(result, dict):
        raise HTTPException(status_code=400, detail="Invalid task result format.")
    
    translated_pdf_path = result.get("output_path")
    if not translated_pdf_path:
        raise HTTPException(status_code=404, detail="Translated PDF path not found.")
        
    base_path = translated_pdf_path.replace('.pdf', '')
    translation_data_path = f"{base_path}_translation_data.json"
    position_data_path = f"{base_path}_translation_data_position.json"
    
    if not Path(position_data_path).exists():
        raise HTTPException(status_code=404, detail="Position data not found, cannot regenerate PDF.")

    with open(translation_data_path, 'w', encoding='utf-8') as f:
        json.dump({"pages": jsonable_encoder(translation_data.pages)}, f, ensure_ascii=False, indent=2)
        
    with open(position_data_path, 'r', encoding='utf-8') as f:
        position_data = json.load(f)
    
    # La tarea `regenerate_pdf` es síncrona por ahora, está bien para este caso.
    # Si fuera larga, se debería convertir en una tarea asíncrona también.
    regenerate_task = celery_app.send_task(
        'regenerate_pdf',
        kwargs={
            'task_id': task_id,
            'translation_data': {"pages": jsonable_encoder(translation_data.pages)},
            'position_data': position_data
        }
    )
    
    try:
        regenerate_result = regenerate_task.get(timeout=60) # Aumentar timeout
        if regenerate_result.get("error"):
            raise HTTPException(500, detail=f"Error regenerating PDF: {regenerate_result['error']}")
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to get regeneration result: {str(e)}")

    return {"message": "Translation data updated and PDF regenerated successfully"}

# El resto de endpoints como descarga del original, etc., no necesitan cambios.
@app.get("/pdfs/download/original/{task_id}")
async def download_original_pdf(task_id: str):
    file_path = UPLOAD_DIR / f"{task_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")
    return FileResponse(
        file_path, 
        media_type="application/pdf", 
        filename=f"{task_id}.pdf",
        headers={
            "Content-Disposition": 'inline; filename="original.pdf"'
        }
    )

@app.get("/")
async def read_root():
    return {"message": "PDF Translator API is running."}

# El endpoint `regenerate_pdf_endpoint` es redundante si `update_translation_data` ya regenera.
# Se puede mantener si se quiere una forma explícita de re-lanzar la regeneración.