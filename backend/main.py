"""Módulo principal de la API para la traducción de documentos PDF.

Este archivo define la aplicación FastAPI, sus middlewares, modelos de datos Pydantic,
y todos los endpoints necesarios para subir, traducir, monitorear y descargar
documentos PDF. Utiliza Celery para el procesamiento asíncrono y S3/MinIO
para el almacenamiento de archivos.
"""

from fastapi import FastAPI, UploadFile, HTTPException, Form, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from enum import Enum
import json
import logging
import os
from typing import Optional, List, Any
from celery import Celery
from celery.result import AsyncResult
from fastapi.encoders import jsonable_encoder

# Imports de almacenamiento
from src.infrastructure.storage.s3 import upload_bytes, download_bytes, presigned_get_url, key_exists
from src.infrastructure.config.settings import settings

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Modelos de datos

class TaskStatus(str, Enum):
    """Enumera los posibles estados finales de una tarea de traducción."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingStep(str, Enum):
    """Enumera los pasos intermedios durante el procesamiento de una traducción."""
    QUEUED = "Iniciando traducción"
    UPLOADING_PDF = "Preparando documento"
    CONVERTING_PDF = "Analizando páginas"
    PROCESSING_PAGES = "Traduciendo contenido"
    COMBINING_PDF = "Finalizando documento"
    UNKNOWN = "Procesando"

class TranslationProgress(BaseModel):
    """Modela el progreso de una tarea, indicando el paso actual y detalles."""
    step: ProcessingStep = ProcessingStep.QUEUED
    details: Optional[Any] = None

class TranslationTask(BaseModel):
    """Modelo de respuesta completo para el estado de una tarea."""
    id: str
    status: TaskStatus
    progress: Optional[TranslationProgress] = None
    error: Optional[str] = None
    originalFile: str
    translatedFile: Optional[str] = None

class UploadResponse(BaseModel):
    """Modelo de respuesta tras subir un archivo para traducir."""
    taskId: str

class TranslationText(BaseModel):
    """Representa un único fragmento de texto original y su traducción."""
    id: int
    original_text: str
    translated_text: str

class PageTranslation(BaseModel):
    """Contiene todas las traducciones de una única página."""
    page_number: int
    translations: List[TranslationText]

class TranslationData(BaseModel):
    """Estructura completa de los datos de traducción de un documento."""
    pages: List[PageTranslation]

# Aplicación FastAPI
app = FastAPI(title="PDF Translator API - S3/MinIO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Funciones auxiliares
def get_final_task_result(task_id: str) -> Optional[AsyncResult]:
    """Sigue la cadena de tareas de Celery para encontrar el resultado final.

    Algunas tareas (orquestadoras) inician otras. Esta función navega
    desde la tarea inicial hasta la tarea final que contiene el resultado
    real.

    :param task_id: El ID de la tarea de Celery inicial (orquestadora).
    :type task_id: str
    :return: El objeto AsyncResult de la tarea final, o la tarea orquestadora si aún no ha terminado.
    :rtype: Optional[AsyncResult]
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

# Endpoints de la API

@app.post("/pdfs/translate", response_model=UploadResponse)
async def translate_pdf_endpoint(
    file: UploadFile = File(...),
    srcLang: str = Form("auto"),
    tgtLang: str = Form("es"),
    languageModel: str = Form("openai/gpt-4o-mini"),
    confidence: float = Form(0.45)
):
    """Recibe un archivo PDF y comienza una tarea de traducción asíncrona.

    Valida que el archivo sea un PDF, lo lee en memoria y lo envía a una
    tarea de Celery para su procesamiento. Devuelve inmediatamente el ID
    de la tarea para su posterior consulta.

    :param file: El archivo PDF a traducir.
    :type file: UploadFile
    :param srcLang: Idioma de origen (o 'auto' para detección automática).
    :type srcLang: str
    :param tgtLang: Idioma de destino.
    :type tgtLang: str
    :param languageModel: Modelo de lenguaje a utilizar para la traducción.
    :type languageModel: str
    :param confidence: Nivel de confianza para el modelo.
    :type confidence: float
    :return: Un objeto JSON con el `taskId` de la tarea iniciada.
    :rtype: UploadResponse
    :raises HTTPException: 400 si el archivo no es PDF, 500 para errores internos.
    """
    try:
        logger.info(f"Iniciando traducción: {file.filename} ({srcLang} -> {tgtLang}) con modelo {languageModel} y confianza {confidence}")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        file_content = await file.read()
        
        result = celery_app.send_task('process_pdf_document', args=[file_content, srcLang, tgtLang, languageModel, confidence])
        
        task_id = result.id
        
        logger.info(f"Tarea de orquestación iniciada con task_id único: {task_id}")
        
        return UploadResponse(taskId=task_id)
        
    except Exception as e:
        logger.error(f"Error en endpoint de traducción: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/pdfs/status/{task_id}")
async def get_task_status(task_id: str):
    """Consulta el estado y progreso de una tarea de traducción.

    Este endpoint mapea el estado interno de Celery a un formato
    comprensible para el frontend, incluyendo el paso actual del proceso.

    :param task_id: El ID de la tarea a consultar.
    :type task_id: str
    :return: Un objeto `TranslationTask` con el estado detallado de la tarea.
    :rtype: dict
    :raises HTTPException: 500 si ocurre un error al consultar el estado.
    """
    try:
        orchestrator_task = AsyncResult(task_id, app=celery_app)
        # ... (el resto del código de la función permanece igual)
        state = orchestrator_task.state
        info = orchestrator_task.info or {}
        
        if state == 'SUCCESS' and isinstance(info, dict) and 'result_task_id' in info:
            final_task_id = info['result_task_id']
            final_task = AsyncResult(final_task_id, app=celery_app)
            final_state = final_task.state
            final_info = final_task.info or {}
            
            if final_state == 'PENDING':
                state = 'PROGRESS'
                info = {'status': 'Traduciendo contenido'}
            else:
                state = final_state
                info = final_info
        
        logger.info(f"Reportando estado para {task_id}: Celery state={state}, info={info}")

        if state == 'PENDING':
            status = TaskStatus.PENDING
            progress = TranslationProgress(step=ProcessingStep.QUEUED)
        elif state == 'PROGRESS':
            status = TaskStatus.PROCESSING
            step_text = info.get('status', 'Procesando...')
            
            step_map = {
                "Preparando documento": ProcessingStep.UPLOADING_PDF,
                "Analizando páginas": ProcessingStep.CONVERTING_PDF,
                "Traduciendo contenido": ProcessingStep.PROCESSING_PAGES,
                "Finalizando documento": ProcessingStep.COMBINING_PDF,
            }
            step = next((s for t, s in step_map.items() if t in step_text), ProcessingStep.UNKNOWN)
            
            progress = TranslationProgress(step=step, details=step_text)
        elif state == 'SUCCESS':
            status = TaskStatus.COMPLETED
            progress = None
        elif state == 'FAILURE':
            status = TaskStatus.FAILED
            progress = None
        else:
            status = TaskStatus.PROCESSING
            progress = TranslationProgress(step=ProcessingStep.UNKNOWN)
        
        error_message = None
        if status == TaskStatus.FAILED:
            error_message = str(orchestrator_task.traceback) if orchestrator_task.traceback else "Error desconocido en la tarea."
        
        task_response = TranslationTask(
            id=task_id,
            status=status,
            progress=progress,
            error=error_message,
            originalFile=f"{task_id}/original.pdf",
            translatedFile=f"{task_id}/translated/translated.pdf" if status == TaskStatus.COMPLETED else None
        )
        
        return jsonable_encoder(task_response)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/pdfs/download/translated/{task_id}")
async def get_translated_pdf(task_id: str):
    """Genera y redirige a una URL prefirmada para descargar el PDF traducido.

    Verifica que la tarea se haya completado con éxito y que el archivo exista
    en S3. Luego, genera una URL de descarga temporal y segura.

    :param task_id: El ID de la tarea completada.
    :type task_id: str
    :return: Una redirección HTTP 307 a la URL de descarga del archivo.
    :rtype: RedirectResponse
    :raises HTTPException: 404 si la tarea o el archivo no se encuentran, 500 para otros errores.
    """
    try:
        final_task = get_final_task_result(task_id)
        if not final_task or final_task.state != 'SUCCESS':
            raise HTTPException(status_code=404, detail="Tarea no completada o no encontrada")
        
        info = final_task.info or {}
        
        if isinstance(info, dict) and 'translated_key' in info:
            translated_key = info['translated_key']
            logger.info(f"Using translated_key from task result: {translated_key}")
        else:
            translated_key = f"{task_id}/translated/translated.pdf"
            logger.warning(f"No translated_key in result, using fallback: {translated_key}")
        
        if not key_exists(translated_key):
            logger.error(f"PDF not found at {translated_key}")
            raise HTTPException(status_code=404, detail="PDF traducido no encontrado")
        
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
    """Genera y redirige a una URL prefirmada para descargar el PDF original.

    :param task_id: El ID de la tarea asociada al PDF original.
    :type task_id: str
    :return: Una redirección HTTP 307 a la URL de descarga del archivo.
    :rtype: RedirectResponse
    :raises HTTPException: 404 si el archivo no se encuentra, 500 para otros errores.
    """
    try:
        original_key = f"{task_id}/original.pdf"
        
        if not key_exists(original_key):
            logger.error(f"Original PDF not found at {original_key}")
            raise HTTPException(status_code=404, detail="PDF original no encontrado")
        
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
    """Obtiene los datos de traducción (texto original y traducido) en formato JSON.

    Este endpoint permite al frontend recuperar los datos de la traducción
    para mostrarlos en una interfaz de edición.

    :param task_id: El ID de la tarea.
    :type task_id: str
    :return: Los datos de traducción en formato JSON.
    :rtype: dict
    :raises HTTPException: 404 si los datos no se encuentran.
    """
    try:
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        
        if not key_exists(translation_key):
            raise HTTPException(status_code=404, detail="Datos de traducción no encontrados")
        
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
    """Obtiene los datos de posición de los textos en el PDF.

    Devuelve un JSON con las coordenadas y dimensiones de cada fragmento
    de texto, necesario para la regeneración del PDF.

    :param task_id: El ID de la tarea.
    :type task_id: str
    :return: Los datos de posición en formato JSON.
    :rtype: dict
    :raises HTTPException: 404 si los datos no se encuentran.
    """
    try:
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        
        if not key_exists(position_key):
            raise HTTPException(status_code=404, detail="Datos de posición no encontrados")
        
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
    """Actualiza los datos de traducción y lanza una tarea para regenerar el PDF.

    Recibe los datos de traducción modificados, los guarda en S3 y luego
    inicia una tarea de Celery para crear un nuevo PDF con los textos actualizados.

    :param task_id: El ID de la tarea a actualizar.
    :type task_id: str
    :param translation_data: El objeto con los datos de traducción actualizados.
    :type translation_data: TranslationData
    :return: Un mensaje de confirmación.
    :rtype: dict
    :raises HTTPException: 404 si los datos de posición no se encuentran, 500 para otros errores.
    """
    try:
        logger.info(f"Actualizando datos de traducción para tarea {task_id}")
        
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        if not key_exists(position_key):
            raise HTTPException(status_code=404, detail="Datos de posición no encontrados")
        
        position_data_bytes = download_bytes(position_key)
        position_data = json.loads(position_data_bytes.decode('utf-8'))
        
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        updated_data = json.dumps(translation_data.dict(), ensure_ascii=False, indent=2).encode()
        upload_bytes(translation_key, updated_data, "application/json")
        
        result = celery_app.send_task('regenerate_pdf_from_storage', args=[task_id, translation_data.dict(), position_data])
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

@app.get("/")
async def root():
    """Endpoint raíz que proporciona información básica de la API.

    :return: Un JSON con un mensaje de bienvenida y detalles de la configuración.
    :rtype: dict
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
    """Endpoint de verificación de salud del servicio.

    Comprueba la conectividad con dependencias críticas, como el bucket S3.

    :return: Un JSON indicando el estado de salud del servicio.
    :rtype: dict
    """
    try:
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