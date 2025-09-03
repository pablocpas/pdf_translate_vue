# tasks.py - Refactorizado para usar S3/MinIO

from celery import Celery, current_task, group, chord
import os
from pathlib import Path
import logging
import json
import tempfile
import time
from typing import List, Dict, Any
from io import BytesIO
import asyncio
import aiohttp

from botocore.exceptions import FlexibleChecksumError


# Imports del proyecto
from src.domain.translator.processor import extract_and_translate_page_data, get_font_for_language, adjust_paragraph_font_size
from src.infrastructure.config.settings import MARGIN, settings
from src.infrastructure.storage.s3 import upload_bytes, download_bytes, presigned_get_url

from src.domain.translator.layout import LayoutElement, Rectangle
from src.domain.translator.processor import extract_and_translate_page_data_async
from src.domain.translator.layout import get_layouts_in_batch

from src.domain.translator.processor import extract_and_translate_page_data_async
from src.domain.translator.layout import get_layouts_in_batch

# Imports de terceros
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from PIL import Image
from pdf2image import convert_from_bytes
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)


async def process_page_with_pipeline_async(page_image: Image.Image, layout: List[Dict], tgt_lang: str, language_model: str) -> Dict[str, Any]:
    """
    Wrapper asíncrono que usa el layout pre-calculado.
    """
    # Usar el pipeline asíncrono con el layout ya disponible
    result = await extract_and_translate_page_data_async(page_image, layout, tgt_lang, language_model)
    return result

def process_page_with_existing_pipeline(page_image: Image.Image, src_lang: str, tgt_lang: str, language_model: str, confidence: float) -> Dict[str, Any]:
    """
    Wrapper para el pipeline existente que procesa una página.
    Convierte objeto Image PIL a archivo temporal para usar con extract_and_translate_page_data.
    """
    # Guardar imagen temporalmente para usar con el pipeline existente
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        page_image.save(temp_file.name, format='PNG')
        temp_path = temp_file.name
    
    try:
        # Usar el pipeline existente con los nuevos parámetros
        result = extract_and_translate_page_data(temp_path, tgt_lang, language_model, confidence)
        return result
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(temp_path)
        except:
            pass

def build_translated_pdf(results_list: List[Dict[str, Any]], task_id: str, target_language: str) -> bytes:
    """
    Construye el PDF traducido a partir de los resultados de las páginas.
    Devuelve bytes del PDF final.
    """
    # Crear PDF en memoria
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer)
    styles = getSampleStyleSheet()
    base_style = styles["Normal"]
    font_name = get_font_for_language(target_language)
    
    # Procesar cada página
    for i, page_data in enumerate(results_list):
        if page_data.get("error"):
            logger.warning(f"Saltando página {i+1} debido a error: {page_data['error']}")
            continue

        dims = page_data["page_dimensions"]
        page_width, page_height = dims["width"], dims["height"]
        pdf_canvas.setPageSize((page_width, page_height))
        
        # Fondo blanco
        pdf_canvas.setFillColorRGB(1, 1, 1)
        pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # Dibujar regiones de imagen
        for img_region in page_data.get("image_regions", []):
            # Descargar imagen de la página desde S3
            page_image_key = f"{task_id}/pages/page_{i:03d}.png"
            try:
                page_image_bytes = download_bytes(page_image_key)
                page_image = Image.open(BytesIO(page_image_bytes))
                
                coords = img_region["coordinates"]
                cropped_img = page_image.crop((
                    max(coords["x1"] - MARGIN, 0), max(coords["y1"] - MARGIN, 0),
                    min(coords["x2"] + MARGIN, page_image.width), min(coords["y2"] + MARGIN, page_image.height)
                ))
                
                img_byte_arr = BytesIO()
                cropped_img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                pos = img_region["position"]
                pdf_canvas.drawImage(ImageReader(img_byte_arr), pos["x"], pos["y"], pos["width"], pos["height"])
            except Exception as e:
                logger.error(f"Error procesando imagen de región en página {i}: {e}")

        # Dibujar regiones de texto traducido
        for text_region in page_data.get("text_regions", []):
            pos = text_region["position"]
            paragraph_style = ParagraphStyle(
                name=f"CustomStyle_p{i}_r{text_region['id']}",
                parent=base_style, fontName=font_name,
                fontSize=max(8, pos["height"] * 0.8), leading=max(8, pos["height"] * 0.8) * 1.2
            )
            p = Paragraph(text_region["translated_text"], paragraph_style)
            p = adjust_paragraph_font_size(p, pos["width"], pos["height"], paragraph_style)
            p.wrapOn(pdf_canvas, pos["width"], pos["height"])
            p.drawOn(pdf_canvas, pos["x"], pos["y"])
        
        pdf_canvas.showPage()

    pdf_canvas.save()
    buffer.seek(0)
    return buffer.getvalue()

@celery_app.task(name='translate_pdf_orchestrator', bind=True)
def translate_pdf_orchestrator(self, file_content: bytes, src_lang: str, tgt_lang: str, language_model: str = "openai/gpt-4o-mini", confidence: float = 0.45):
    try:
        task_id = self.request.id
        logger.info(f"Iniciando orquestación para tarea {task_id}")
        
        # 1. Subir PDF y convertir a imágenes (sin cambios)
        self.update_state(state='PROGRESS', meta={'status': 'Preparando documento'})
        original_key = f"{task_id}/original.pdf"
        upload_bytes(original_key, file_content, content_type="application/pdf")
        
        self.update_state(state='PROGRESS', meta={'status': 'Analizando páginas'})
        images = convert_from_bytes(file_content, fmt="png", dpi=300)
        if not images:
            raise Exception("No se pudieron generar imágenes del PDF.")
        
        # 2. Subir imágenes a S3 (sin cambios)
        page_keys = []
        for idx, img in enumerate(images):
            buf = BytesIO()
            img.save(buf, format="PNG")
            png_key = f"{task_id}/pages/page_{idx:03d}.png"
            upload_bytes(png_key, buf.getvalue(), content_type="image/png")
            page_keys.append(png_key)
        
        logger.info(f"Subidas {len(page_keys)} imágenes a S3")
        
        # 3. MODIFICADO: Lanzar UNA tarea para el análisis de layout en lote
        self.update_state(state='PROGRESS', meta={'status': 'Analizando estructura del documento'})
        
        # En lugar de un chord, ahora encadenamos tareas. El resultado de esta llamada
        # contendrá el ID de la tarea finalizadora.
        result_task = batch_layout_analysis_task.delay(
            task_id, page_keys, src_lang, tgt_lang, language_model, confidence, original_key
        )
        
        logger.info(f"Tarea de análisis de layout en lote iniciada: {result_task.id}")
        
        return {
            'status': 'PROCESSING',
            'message': f'Análisis de layout en lote iniciado para {len(page_keys)} páginas.',
            'result_task_id': result_task.id # El cliente puede seguir esta tarea
        }
        
    except Exception as e:
        logger.error(f"Error en orquestación: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}


@celery_app.task(name='batch_layout_analysis_task', bind=True)
def batch_layout_analysis_task(self, task_id: str, page_keys: List[str], src_lang: str, tgt_lang: str, language_model: str, confidence: float, original_key: str):
    try:
        logger.info(f"Iniciando análisis de layout en lote para tarea {task_id}")
        
        # 1. Descargar todas las imágenes desde S3
        images = [Image.open(BytesIO(download_bytes(key))).convert("RGB") for key in page_keys]
        
        # 2. Obtener layouts en un solo lote
        layouts_data = get_layouts_in_batch(images, confidence=confidence)
        
        if len(layouts_data) != len(page_keys):
            raise Exception("El número de layouts no coincide con el número de páginas.")
        
        logger.info(f"Layouts generados para {len(layouts_data)} páginas.")
        self.update_state(state='PROGRESS', meta={'status': 'Traduciendo contenido'})

        # 3. Lanzar procesamiento paralelo de traducción con un chord
        job = group(
            translate_page_content_task.s(task_id, i, key, layout, src_lang, tgt_lang, language_model) 
            for i, (key, layout) in enumerate(zip(page_keys, layouts_data))
        )
        
        # El resultado del chord se enviará a la tarea finalizadora
        result = chord(job)(finalize_task.s(task_id, original_key, src_lang, tgt_lang))
        
        logger.info(f"Chord de traducción iniciado. Tarea finalizadora ID: {result.id}")
        # Devolvemos el ID de la tarea finalizadora para seguimiento
        return {'status': 'Translation tasks dispatched', 'finalize_task_id': result.id}

    except Exception as e:
        logger.error(f"Error en análisis de layout en lote: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        # Aquí podrías notificar a la tarea finalizadora que algo falló, o manejarlo de otra forma.
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name='translate_page_content_task', 
    bind=True,
    autoretry_for=(FlexibleChecksumError,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60
)
def translate_page_content_task(self, task_id: str, page_number: int, image_key: str, layout_data: List[Dict], src_lang: str, tgt_lang: str, language_model: str):
    try:
        logger.info(f"Traduciendo contenido de página {page_number} para tarea {task_id}")


        rehydrated_layout = [
            LayoutElement(box=Rectangle(*elem[0]), type=elem[1], score=elem[2])
            for elem in layout_data
        ]
        
        
        # 1. Descargar imagen desde S3
        img_bytes = download_bytes(image_key)
        page_image = Image.open(BytesIO(img_bytes)).convert("RGB")
        
        # 2. Procesar página con el pipeline asíncrono
        # Ejecutamos el código asíncrono dentro de la tarea síncrona de Celery
        result = asyncio.run(
            process_page_with_pipeline_async(page_image, rehydrated_layout, tgt_lang, language_model)
        )
        
        # 3. Añadir metadatos
        result["page_number"] = page_number
        result["error"] = None
        
        logger.info(f"Página {page_number} traducida exitosamente")
        return result
    except FlexibleChecksumError as e:
        logger.warning(f"Checksum error en página {page_number}. Reintentando... Error: {e}")
        raise e  # Relanzar la excepción para que Celery la capture y reintente


    except Exception as e:
        logger.error(f"Error traduciendo página {page_number}: {e}", exc_info=True)
        return {
            "page_number": page_number, "text_regions": [], "image_regions": [],
            "page_dimensions": None, "error": str(e),
        }




@celery_app.task(
    name='process_page_task', 
    bind=True,
    # Configuración de reintentos:
    autoretry_for=(FlexibleChecksumError,), # Reintenta SÓLO para este error
    retry_kwargs={'max_retries': 3},       # Inténtalo un máximo de 3 veces
    retry_backoff=True,                    # Espera exponencial entre reintentos (e.g., 1s, 2s, 4s)
    retry_backoff_max=60                   # Espera máxima de 60 segundos
)
def process_page_task(self, task_id: str, page_number: int, image_key: str, src_lang: str, tgt_lang: str, language_model: str, confidence: float):
    """
    Tarea worker: descarga imagen de S3, procesa página y devuelve resultados.
    """
    try:
        logger.info(f"Procesando página {page_number} de tarea {task_id}: {image_key}")
        
        # 1. Descargar imagen desde S3
        img_bytes = download_bytes(image_key)
        page_image = Image.open(BytesIO(img_bytes)).convert("RGB")
        
        # 2. Procesar página con pipeline existente
        result = process_page_with_existing_pipeline(page_image, src_lang, tgt_lang, language_model, confidence)
        
        # 3. Añadir número de página
        result["page_number"] = page_number
        result["error"] = None
        
        logger.info(f"Página {page_number} procesada exitosamente")
        return result
    
    except FlexibleChecksumError as e:
        # Celery gestionará el reintento automáticamente gracias a 'autoretry_for'.
        # Este bloque se ejecutará, pero la tarea será reenviada.
        logger.warning(f"Checksum error en página {page_number}. Reintentando... Error: {e}")
        raise # Es importante relanzar la excepción para que Celery la capture.
        
    except Exception as e:
        logger.error(f"Error procesando página {page_number}: {e}", exc_info=True)
        # Devolver error mapeado para evitar que reviente el chord
        return {
            "page_number": page_number,
            "text_regions": [],
            "image_regions": [],
            "page_dimensions": None,
            "error": str(e),
        }


@celery_app.task(name='finalize_task', bind=True)
def finalize_task(self, results_list: List[Dict[str, Any]], task_id: str, original_key: str, src_lang: str, tgt_lang: str):
    """
    Tarea finalizadora: reconstruye PDF traducido y lo sube a S3.
    """
    try:
        logger.info(f"Finalizando tarea {task_id} con {len(results_list)} páginas")
        
        # 1. Ordenar resultados por número de página
        results_list.sort(key=lambda r: r.get("page_number", 0))
        
        self.update_state(state='PROGRESS', meta={'status': 'Finalizando documento'})
        
        # 2. Construir PDF traducido
        start_pdf_build = time.time()
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, tgt_lang)
        pdf_build_time = time.time() - start_pdf_build
        logger.info(f"=== PDF RECONSTRUCTION TIMING ===")
        logger.info(f"PDF reconstruction: {pdf_build_time:.3f}s")
        logger.info("=" * 40)
        
        # 3. Subir PDF final a S3
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        # 4. Construir y subir metadatos de traducción
        translation_data = {
            "pages": [
                {
                    "page_number": page_data.get('page_number', i),
                    "translations": [
                        {
                            "id": text_region["id"],
                            "original_text": text_region["original_text"],
                            "translated_text": text_region["translated_text"]
                        }
                        for text_region in page_data.get("text_regions", [])
                    ]
                }
                for i, page_data in enumerate(results_list) if not page_data.get("error")
            ]
        }
        
        position_data = {
            "pages": [
                {
                    "page_number": page_data.get('page_number', i),
                    "dimensions": page_data["page_dimensions"],
                    "regions": [
                        {
                            "id": text_region["id"],
                            "position": text_region["position"]
                        }
                        for text_region in page_data.get("text_regions", [])
                    ],
                    "image_regions": page_data.get("image_regions", [])
                }
                for i, page_data in enumerate(results_list) if not page_data.get("error")
            ]
        }
        
        # 5. Subir metadatos a S3
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        
        upload_bytes(translation_key, json.dumps(translation_data, ensure_ascii=False, indent=2).encode(), "application/json")
        upload_bytes(position_key, json.dumps(position_data, ensure_ascii=False, indent=2).encode(), "application/json")
        
        # 6. Generar metadatos de resultado
        errors = [r["error"] for r in results_list if r["error"]]
        
        meta_data = {
            "pages": len(results_list),
            "errors": errors,
            "completed_at": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}}),
            "src_lang": src_lang,
            "tgt_lang": tgt_lang
        }
        
        meta_key = f"{task_id}/translated/metadata.json"
        upload_bytes(meta_key, json.dumps(meta_data, ensure_ascii=False, indent=2).encode(), "application/json")
        
        logger.info(f"Tarea {task_id} completada exitosamente")
        
        return {
            "status": "COMPLETED",
            "translated_key": translated_key,
            "translation_data_key": translation_key,
            "position_data_key": position_key,
            "meta_key": meta_key,
            "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Error en finalización de tarea {task_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}




@celery_app.task(name='regenerate_pdf_s3')
def regenerate_pdf_s3_task(task_id: str, translation_data: dict, position_data: dict):
    """
    Regenera PDF desde S3 con nuevos datos de traducción.
    """
    try:
        logger.info(f"Regenerando PDF desde S3 para tarea {task_id}")
        
        # Descargar PDF original y metadatos
        original_key = f"{task_id}/original.pdf"
        
        # Determinar idioma de destino
        first_page = translation_data.get("pages", [])[0] if "pages" in translation_data else None
        first_translation = first_page.get("translations", [])[0] if first_page else None
        target_language = first_translation.get("target_language", "es") if first_translation else "es"
        
        # Simular results_list para reutilizar build_translated_pdf
        results_list = []
        for page in translation_data.get("pages", []):
            page_num = page["page_number"]
            
            # Buscar dimensiones en position_data
            page_pos = next((p for p in position_data.get("pages", []) if p["page_number"] == page_num), None)
            dimensions = page_pos["dimensions"] if page_pos else {"width": 595, "height": 842}  # A4 default
            
            # Construir regiones de texto
            text_regions = []
            for trans in page["translations"]:
                # Buscar posición
                region_pos = next((r for r in page_pos.get("regions", []) if r["id"] == trans["id"]), None)
                if region_pos:
                    text_regions.append({
                        "id": trans["id"],
                        "original_text": trans["original_text"],
                        "translated_text": trans["translated_text"],
                        "position": region_pos["position"]
                    })
            
            # Obtener image_regions guardadas
            image_regions = page_pos.get("image_regions", []) if page_pos else []
            
            results_list.append({
                "page_number": page_num,
                "page_dimensions": dimensions,
                "text_regions": text_regions,
                "image_regions": image_regions,
                "error": None
            })
        
        # Generar PDF
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, target_language)
        
        # Subir PDF regenerado
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        logger.info(f"PDF regenerado exitosamente para tarea {task_id}")
        
        return {
            "success": True,
            "translated_key": translated_key
        }
        
    except Exception as e:
        logger.error(f"Error regenerando PDF S3 para tarea {task_id}: {e}", exc_info=True)
        return {
            "error": str(e)
        }


@celery_app.task(name='test_async_calls')
def test_async_calls():
    """
    Prueba de concepto: tarea Celery que hace llamadas asíncronas.
    """
    async def make_async_request(url: str):
        """Función asíncrona para hacer una petición HTTP"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    text = await response.text()
                    return {
                        'url': url,
                        'status': response.status,
                        'headers': dict(response.headers),
                        'text': text[:200]  # Solo primeros 200 caracteres
                    }
        except Exception as e:
            return {'url': url, 'error': str(e)}
    
    async def test_multiple_requests():
        """Función que hace múltiples peticiones concurrentemente"""
        urls = [
            'https://httpbin.org/get',
            'https://httpbin.org/uuid',
            'https://httpbin.org/delay/1'
        ]
        
        # Ejecutar peticiones concurrentemente
        tasks = [make_async_request(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'message': 'Async calls completed successfully',
            'results_count': len(results),
            'results': results
        }
    
    try:
        logger.info("Iniciando prueba de llamadas asíncronas en tarea Celery")
        
        # Ejecutar el código asíncrono dentro de la tarea síncrona de Celery
        start_time = time.time()
        result = asyncio.run(test_multiple_requests())
        execution_time = time.time() - start_time
        
        result['execution_time'] = execution_time
        result['timestamp'] = time.time()
        
        logger.info(f"Prueba async completada en {execution_time:.3f}s")
        return result
        
    except Exception as e:
        logger.error(f"Error en prueba async: {e}", exc_info=True)
        return {
            'error': str(e),
            'message': 'Failed to execute async calls'
        }