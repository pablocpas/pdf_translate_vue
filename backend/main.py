from fastapi import FastAPI, UploadFile, HTTPException, Form, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
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

# S3/MinIO imports
from src.infrastructure.storage.s3 import upload_bytes, download_bytes, presigned_get_url, key_exists
from src.infrastructure.config.settings import settings

# --- Configuración ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Mantener directorios locales para compatibilidad hacia atrás
UPLOAD_DIR = Path(os.getenv('UPLOAD_FOLDER', '/app/uploads'))
TRANSLATED_DIR = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSLATED_DIR.mkdir(exist_ok=True)

logger.info(f"Upload directory: {UPLOAD_DIR}")
logger.info(f"Translated directory: {TRANSLATED_DIR}")
# --- Modelos Pydantic ---

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
    details: Optional[Any] = None

class TranslationTask(BaseModel):
    id: str
    status: TaskStatus
    progress: Optional[TranslationProgress] = None
    error: Optional[str] = None
    originalFile: str
    translatedFile: Optional[str] = None

class UploadResponse(BaseModel):
    taskId: str

class TranslationText(BaseModel):
    id: int
    original_text: str
    translated_text: str

class PageTranslation(BaseModel):
    page_number: int
    translations: List[TranslationText]

class TranslationData(BaseModel):
    pages: List[PageTranslation]

# --- Instancia de FastAPI ---
app = FastAPI(title="PDF Translator API - S3/MinIO")

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
    
    if orchestrator_task.state == 'FAILURE':
        return orchestrator_task
    
    if orchestrator_task.state == 'SUCCESS':
        try:
            result = orchestrator_task.result
            if isinstance(result, dict) and 'result_task_id' in result:
                final_task_id = result['result_task_id']
                return AsyncResult(final_task_id, app=celery_app)
        except Exception as e:
            logger.warning(f"Error obteniendo resultado final de {task_id}: {e}")
            return orchestrator_task
    
    return orchestrator_task

# --- ENDPOINTS ---

@app.post("/pdfs/translate", response_model=UploadResponse)
async def translate_pdf_endpoint(
    file: UploadFile = File(...),
    srcLang: str = Form("auto"),
    tgtLang: str = Form("es"),
    modelType: str = Form("primalayout")
):
    """
    Endpoint para subir PDF y iniciar traducción usando S3/MinIO.
    """
    try:
        logger.info(f"Iniciando traducción: {file.filename} ({srcLang} -> {tgtLang})")
        
        # Validar archivo
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Leer contenido del archivo
        file_content = await file.read()
        
        # Lanzar tarea de orquestación S3 PRIMERO para obtener el ID de Celery
        result = celery_app.send_task('translate_pdf_orchestrator', args=[file_content, srcLang, tgtLang, modelType])
        
        # Usar el ID de Celery como task_id único para todo
        task_id = result.id
        
        logger.info(f"Tarea de orquestación iniciada con task_id único: {task_id}")
        
        return UploadResponse(taskId=task_id)
        
    except Exception as e:
        logger.error(f"Error en endpoint de traducción: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/pdfs/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Obtiene el estado de una tarea de traducción.
    """
    try:
        # El task_id ahora ES el Celery ID directamente
        orchestrator_task = AsyncResult(task_id, app=celery_app)
        
        logger.info(f"Checking status for task {task_id}: state={orchestrator_task.state}")
        
        state = orchestrator_task.state
        info = orchestrator_task.info or {}
        
        # Si el orquestador completó exitosamente, SIEMPRE verificar la tarea finalizadora
        if state == 'SUCCESS' and isinstance(info, dict) and 'result_task_id' in info:
            final_task_id = info['result_task_id']
            final_task = AsyncResult(final_task_id, app=celery_app)
            logger.info(f"Final task {final_task_id}: state={final_task.state}")
            
            # SIEMPRE usar el estado de la tarea finalizadora
            state = final_task.state
            info = final_task.info or {}
            
            # Si la tarea finalizadora aún está pendiente o en progreso, verificar si el PDF ya existe
            if state in ['PENDING', 'PROGRESS']:
                # FALLBACK: Verificar si el PDF ya se creó aunque la tarea parezca pendiente
                logger.info(f"Final task appears {state}, checking if PDF exists as fallback")
                translated_key = f"{task_id}/translated/translated.pdf"
                if key_exists(translated_key):
                    logger.info(f"PDF found despite task state {state}, marking as SUCCESS")
                    state = 'SUCCESS'
                    info = {'status': 'DONE', 'translated_key': translated_key}
                else:
                    state = 'PROGRESS'
                    if not info:
                        info = {'status': 'Finalizando traducción...'}
        elif state == 'SUCCESS':
            # Si no hay result_task_id, algo está mal - mantener en progreso
            logger.warning(f"Orchestrator completed but no result_task_id found for {task_id}")
            state = 'PROGRESS'
            info = {'status': 'Procesando resultado...'}
        
        logger.info(f"Final mapped state for {task_id}: {state}, info: {info}")
        
        # Mapear estados de Celery a nuestros estados
        if state == 'PENDING':
            status = TaskStatus.PENDING
            progress = TranslationProgress(step=ProcessingStep.QUEUED)
        elif state == 'PROGRESS':
            status = TaskStatus.PROCESSING
            step_text = info.get('status', 'Procesando...')
            # Mapear texto a enum
            if 'Convirtiendo' in step_text:
                step = ProcessingStep.CONVERTING_PDF
            elif 'paralelo' in step_text:
                step = ProcessingStep.PROCESSING_PAGES
            elif 'Ensamblando' in step_text or 'Reconstruyendo' in step_text:
                step = ProcessingStep.COMBINING_PDF
            else:
                step = ProcessingStep.UNKNOWN
            progress = TranslationProgress(step=step, details=step_text)
        elif state == 'SUCCESS':
            # Verificar que el PDF traducido realmente existe antes de marcar como completado
            # Usar el translated_key del resultado si está disponible
            if isinstance(info, dict) and 'translated_key' in info:
                translated_key = info['translated_key']
                logger.info(f"Using translated_key from result: {translated_key}")
            else:
                translated_key = f"{task_id}/translated/translated.pdf"
                logger.info(f"Using default translated_key: {translated_key}")
            
            if key_exists(translated_key):
                status = TaskStatus.COMPLETED
                progress = TranslationProgress(step=ProcessingStep.COMBINING_PDF)
                logger.info(f"Task {task_id} confirmed complete - PDF exists in S3 at {translated_key}")
            else:
                # PDF no existe aún, mantener como procesando
                logger.warning(f"Task {task_id} marked SUCCESS but PDF not found in S3 at {translated_key}, keeping as PROCESSING")
                status = TaskStatus.PROCESSING
                progress = TranslationProgress(step=ProcessingStep.COMBINING_PDF, details="Finalizando...")
                state = 'PROGRESS'  # Override para logging
        elif state == 'FAILURE':
            status = TaskStatus.FAILED
            progress = None
        else:
            status = TaskStatus.PROCESSING
            progress = TranslationProgress(step=ProcessingStep.UNKNOWN)
        
        # Construir respuesta
        task_response = TranslationTask(
            id=task_id,
            status=status,
            progress=progress,
            error=str(info.get('exc_message', '')) if state == 'FAILURE' else None,
            originalFile=f"{task_id}/original.pdf",
            translatedFile=f"{task_id}/translated/translated.pdf" if status == TaskStatus.COMPLETED else None
        )
        
        return jsonable_encoder(task_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/pdfs/download/translated/{task_id}")
async def get_translated_pdf(task_id: str):
    """
    Devuelve URL prefirmada para visualizar el PDF traducido.
    """
    try:
        # Obtener la clave real del resultado de la tarea
        final_task = get_final_task_result(task_id)
        if not final_task or final_task.state != 'SUCCESS':
            raise HTTPException(status_code=404, detail="Tarea no completada o no encontrada")
        
        info = final_task.info or {}
        
        # Usar translated_key del resultado si está disponible
        if isinstance(info, dict) and 'translated_key' in info:
            translated_key = info['translated_key']
            logger.info(f"Using translated_key from task result: {translated_key}")
        else:
            # Fallback al patrón tradicional
            translated_key = f"{task_id}/translated/translated.pdf"
            logger.warning(f"No translated_key in result, using fallback: {translated_key}")
        
        # Verificar que el PDF existe en S3
        if not key_exists(translated_key):
            logger.error(f"PDF not found at {translated_key}")
            raise HTTPException(status_code=404, detail="PDF traducido no encontrado")
        
        # Generar URL prefirmada
        url = presigned_get_url(
            translated_key,
            expires=3600,
            inline_filename=f"{task_id}_translated.pdf",
            content_type="application/pdf"
        )
        
        logger.info(f"URL prefirmada generada para {task_id} -> {translated_key}")
        
        return RedirectResponse(url=url)

        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando URL para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/pdfs/download/original/{task_id}")
async def get_original_pdf(task_id: str):
    """
    Devuelve URL prefirmada para visualizar el PDF original.
    """
    try:
        original_key = f"{task_id}/original.pdf"
        
        # Verificar que el PDF original existe en S3
        if not key_exists(original_key):
            logger.error(f"Original PDF not found at {original_key}")
            raise HTTPException(status_code=404, detail="PDF original no encontrado")
        
        # Generar URL prefirmada
        url = presigned_get_url(
            original_key,
            expires=3600,
            inline_filename=f"{task_id}_original.pdf",
            content_type="application/pdf"
        )
        
        logger.info(f"URL prefirmada generada para PDF original {task_id} -> {original_key}")
        
        return RedirectResponse(url=url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando URL para PDF original {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/pdfs/translation-data/{task_id}")
async def get_translation_data(task_id: str):
    """
    Devuelve los datos de traducción para edición.
    """
    try:
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        
        if not key_exists(translation_key):
            raise HTTPException(status_code=404, detail="Datos de traducción no encontrados")
        
        # Descargar datos desde S3
        data_bytes = download_bytes(translation_key)
        translation_data = json.loads(data_bytes.decode('utf-8'))
        
        return translation_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo datos de traducción para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/pdfs/translated/{task_id}/position")
async def get_position_data(task_id: str):
    """
    Devuelve los datos de posición para edición.
    """
    try:
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        
        if not key_exists(position_key):
            raise HTTPException(status_code=404, detail="Datos de posición no encontrados")
        
        # Descargar datos desde S3
        data_bytes = download_bytes(position_key)
        position_data = json.loads(data_bytes.decode('utf-8'))
        
        return position_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo datos de posición para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/pdfs/translation-data/{task_id}")
async def update_translation_data(task_id: str, translation_data: TranslationData = Body(...)):
    """
    Actualiza los datos de traducción y regenera el PDF.
    """
    try:
        logger.info(f"Actualizando datos de traducción para tarea {task_id}")
        
        # Obtener datos de posición actuales
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        if not key_exists(position_key):
            raise HTTPException(status_code=404, detail="Datos de posición no encontrados")
        
        position_data_bytes = download_bytes(position_key)
        position_data = json.loads(position_data_bytes.decode('utf-8'))
        
        # Actualizar datos de traducción en S3
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        updated_data = json.dumps(translation_data.dict(), ensure_ascii=False, indent=2).encode()
        upload_bytes(translation_key, updated_data, "application/json")
        
        # Regenerar PDF con nuevos datos
        result = celery_app.send_task('regenerate_pdf_s3', args=[task_id, translation_data.dict(), position_data])
        task_result = result.get(timeout=60)
        
        if "error" in task_result:
            raise HTTPException(status_code=500, detail=f"Error regenerando PDF: {task_result['error']}")
        
        logger.info(f"Datos de traducción actualizados para tarea {task_id}")
        return {"success": True, "message": "Traducción actualizada correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando traducción para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/pdfs/regenerate/{task_id}")
async def regenerate_pdf_endpoint(
    task_id: str,
    translation_data: TranslationData = Body(...),
    position_data: dict = Body(...)
):
    """
    Regenera el PDF con nuevos datos de traducción usando S3.
    """
    try:
        logger.info(f"Regenerando PDF para tarea {task_id}")
        
        # Lanzar tarea de regeneración
        result = celery_app.send_task('regenerate_pdf_s3', args=[task_id, translation_data.dict(), position_data])
        
        # Esperar resultado (puede ser mejorado con polling asíncrono)
        task_result = result.get(timeout=60)
        
        if "error" in task_result:
            raise HTTPException(status_code=500, detail=f"Error regenerando PDF: {task_result['error']}")
        
        logger.info(f"PDF regenerado exitosamente para tarea {task_id}")
        
        return {"success": True, "message": "PDF regenerado correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerando PDF para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- ENDPOINTS DE COMPATIBILIDAD HACIA ATRÁS ---

@app.get("/pdfs/original/{task_id}")
async def get_original_pdf_legacy(task_id: str):
    """
    LEGACY: Devuelve URL del PDF original desde S3.
    """
    try:
        original_key = f"{task_id}/original.pdf"
        
        if not key_exists(original_key):
            # Intentar con archivo local como fallback
            local_path = UPLOAD_DIR / f"{task_id}.pdf"
            if local_path.exists():
                return FileResponse(str(local_path), media_type="application/pdf")
            raise HTTPException(status_code=404, detail="PDF original no encontrado")
        
        url = presigned_get_url(
            original_key,
            expires=3600,
            inline_filename=f"{task_id}_original.pdf"
        )
        
        return {"url": url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo PDF original para {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/")
async def root():
    """
    Endpoint raíz con información del sistema.
    """
    return {
        "message": "PDF Translator API - S3/MinIO Version",
        "version": "2.0.0",
        "storage": "S3/MinIO",
        "bucket": settings.AWS_S3_BUCKET,
        "endpoint": settings.AWS_S3_ENDPOINT_URL
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    try:
        # Verificar conexión con S3
        from src.infrastructure.storage.s3 import _client
        _client.head_bucket(Bucket=settings.AWS_S3_BUCKET)
        
        return {
            "status": "healthy",
            "s3_connection": "ok",
            "bucket": settings.AWS_S3_BUCKET
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "s3_connection": "error",
            "error": str(e)
        }