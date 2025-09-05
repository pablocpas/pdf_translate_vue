"""Módulo principal de tareas Celery para el procesamiento de documentos PDF.

Este archivo define el flujo de trabajo asíncrono para la traducción de PDFs.
Contiene la tarea orquestadora principal que divide el trabajo, las tareas
que procesan lotes de páginas en paralelo, y la tarea finalizadora que
ensambla el documento traducido.

**Flujo de trabajo principal:**

1.  **process_pdf_document**:
    Orquesta todo el proceso. Convierte PDF a imágenes,
    crea lotes de páginas y lanza un `chord` de Celery.

2.  **extract_and_translate_batch**:
    Tarea ejecutada en paralelo para cada lote.
    Realiza la detección de layout, OCR y traducción.

3.  **assemble_final_pdf**:
    Tarea finalizadora del `chord`. Recopila los resultados
    de todos los lotes, construye el PDF final y guarda los metadatos.

4.  **regenerate_pdf_from_storage**:
    Tarea independiente para regenerar un PDF
    a partir de datos de traducción previamente guardados y modificados.
"""
from celery import Celery, group, chord
import os
import logging
import json
import time
from typing import List, Dict, Any, Tuple
from io import BytesIO

from botocore.exceptions import FlexibleChecksumError
from PIL import Image
from pdf2image import convert_from_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
import asyncio

# Imports del proyecto
from src.domain.translator.processor import extract_page_data_in_batch
from src.domain.translator.utils import get_font_for_language, adjust_paragraph_font_size
from src.infrastructure.config.settings import MARGIN, settings
from src.infrastructure.storage.s3 import upload_bytes, download_bytes

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# CONSTANTES DE CONFIGURACIÓN
PAGE_PROCESSING_BATCH_SIZE = 16

# =============================================================================
# UTILIDADES PARA CONSTRUCCIÓN DE PDF
# =============================================================================

def build_translated_pdf(results_list: List[Dict[str, Any]], task_id: str, target_language: str) -> bytes:
    """Construye un documento PDF a partir de una lista de datos de página procesados.

    Itera sobre los datos de cada página, dibuja las regiones de imagen recortadas
    y renderiza los párrafos de texto traducido en sus posiciones correspondientes.

    :param results_list: Lista de diccionarios, cada uno representando una página
                         con sus regiones de texto, imagen y dimensiones.
    :type results_list: List[Dict[str, Any]]
    :param task_id: El ID de la tarea, usado para descargar imágenes de página desde S3.
    :type task_id: str
    :param target_language: El código del idioma de destino para seleccionar la fuente adecuada.
    :type target_language: str
    :return: El documento PDF completo como un objeto de bytes.
    :rtype: bytes
    """
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer)
    styles = getSampleStyleSheet()
    base_style = styles["Normal"]
    font_name = get_font_for_language(target_language)
    
    for i, page_data in enumerate(results_list):
        if page_data.get("error"):
            logger.warning(f"Omitiendo página {i+1} por error: {page_data['error']}")
            continue

        if not page_data.get("page_dimensions"):
            logger.warning(f"Omitiendo página {i+1} por falta de dimensiones.")
            continue
            
        dims = page_data["page_dimensions"]
        page_width, page_height = dims["width"], dims["height"]
        pdf_canvas.setPageSize((page_width, page_height))
        
        pdf_canvas.setFillColorRGB(1, 1, 1)
        pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        for img_region in page_data.get("image_regions", []):
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

# =============================================================================
# DEFINICIÓN DE TAREAS CELERY
# =============================================================================

@celery_app.task(name='process_pdf_document', bind=True)
def process_pdf_document(self, file_content: bytes, src_lang: str, tgt_lang: str, language_model: str = "openai/gpt-4o-mini", confidence: float = 0.45):
    """Tarea orquestadora principal que inicia el flujo de traducción de un PDF.

    Sube el PDF original, lo convierte en imágenes por página, agrupa las páginas
    en lotes y lanza un `chord` de Celery para procesar los lotes en paralelo. La
    tarea finalizadora del `chord` (`assemble_final_pdf`) se encargará de unir los resultados.

    :param self: La instancia de la tarea de Celery (inyectada por `bind=True`).
    :param file_content: El contenido del archivo PDF en bytes.
    :type file_content: bytes
    :param src_lang: Código del idioma de origen.
    :type src_lang: str
    :param tgt_lang: Código del idioma de destino.
    :type tgt_lang: str
    :param language_model: Identificador del modelo de IA a usar para la traducción.
    :type language_model: str
    :param confidence: Umbral de confianza para la detección de layout.
    :type confidence: float
    :return: Un diccionario con el estado del proceso y el ID de la tarea finalizadora.
    :rtype: dict
    """
    try:
        task_id = self.request.id
        logger.info(f"Iniciando orquestación por lotes para tarea {task_id}")
        
        self.update_state(state='PROGRESS', meta={'status': 'Preparando documento'})
        original_key = f"{task_id}/original.pdf"
        upload_bytes(original_key, file_content, content_type="application/pdf")
        
        self.update_state(state='PROGRESS', meta={'status': 'Analizando páginas'})
        images = convert_from_bytes(file_content, fmt="png", dpi=300)
        if not images:
            raise Exception("No se pudieron generar imágenes del PDF.")
        
        page_info = []
        for idx, img in enumerate(images):
            buf = BytesIO()
            img.save(buf, format="PNG")
            png_key = f"{task_id}/pages/page_{idx:03d}.png"
            upload_bytes(png_key, buf.getvalue(), content_type="image/png")
            page_info.append((idx, png_key))
        
        logger.info(f"Subidas {len(page_info)} imágenes. Creando lotes de tamaño {PAGE_PROCESSING_BATCH_SIZE}.")
        
        batches = [
            page_info[i:i + PAGE_PROCESSING_BATCH_SIZE] 
            for i in range(0, len(page_info), PAGE_PROCESSING_BATCH_SIZE)
        ]
        
        self.update_state(state='PROGRESS', meta={'status': 'Extrayendo contenido (sin traducción)'})
        
        job = group(
            extract_and_translate_batch.s(task_id, batch, src_lang, tgt_lang, language_model, confidence) 
            for batch in batches
        )
        
        result = chord(job)(assemble_final_pdf.s(task_id, original_key, src_lang, tgt_lang))
        
        logger.info(f"Chord iniciado para {len(batches)} lotes. Tarea finalizadora ID: {result.id}")
        
        return {
            'status': 'PROCESSING',
            'message': f'Procesamiento en {len(batches)} lotes iniciado para {len(page_info)} páginas.',
            'result_task_id': result.id
        }
        
    except Exception as e:
        logger.error(f"Error en orquestación: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}

async def translate_extracted_text(extracted_data: List[Dict[str, Any]], tgt_lang: str, language_model: str) -> List[Dict[str, Any]]:
    """Gestiona llamadas concurrentes a la API de traducción para un lote de páginas.

    Utiliza `asyncio.gather` para realizar todas las solicitudes de traducción
    de un lote de forma paralela, mejorando significativamente el rendimiento.

    :param extracted_data: Lista de datos de página, cada una con regiones de texto extraídas.
    :type extracted_data: List[Dict[str, Any]]
    :param tgt_lang: Código del idioma de destino.
    :type tgt_lang: str
    :param language_model: Identificador del modelo de IA.
    :type language_model: str
    :return: La misma estructura de datos de entrada, pero con el campo `translated_text`
             añadido a cada región de texto.
    :rtype: List[Dict[str, Any]]
    """
    translation_coroutines = []
    for page_data in extracted_data:
        original_texts = [region["original_text"] for region in page_data.get("text_regions", [])]
        coroutine = translate_text_async(original_texts, tgt_lang, language_model)
        translation_coroutines.append(coroutine)
    
    if not translation_coroutines:
        logger.info("No text to translate in this batch.")
        return extracted_data

    logger.info(f"Lanzando {len(translation_coroutines)} tareas de traducción en paralelo...")
    all_translated_results = await asyncio.gather(*translation_coroutines)
    logger.info("Todas las tareas de traducción han finalizado.")

    for i, page_data in enumerate(extracted_data):
        translated_texts = all_translated_results[i]
        text_regions = page_data.get("text_regions", [])
        
        if len(translated_texts) == len(text_regions):
            for j, region in enumerate(text_regions):
                region["translated_text"] = translated_texts[j]
        else:
            logger.warning(f"Discrepancia de traducción en página del lote {i}. Se usará texto original.")
            for region in text_regions:
                region["translated_text"] = region["original_text"]
    
    return extracted_data

@celery_app.task(
    name='extract_and_translate_batch', 
    bind=True,
    autoretry_for=(FlexibleChecksumError,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60
)
def extract_and_translate_batch(self, task_id: str, page_batch_info: List[Tuple[int, str]], src_lang: str, tgt_lang: str, language_model: str, confidence: float):
    """Tarea de worker que procesa un lote de páginas.

    Realiza la detección de layout, OCR y traducción para un conjunto de páginas.
    Está diseñada para ser ejecutada en paralelo por múltiples workers de Celery.

    :param self: Instancia de la tarea de Celery.
    :param task_id: Identificador único de la tarea global.
    :type task_id: str
    :param page_batch_info: Lista de tuplas `(page_number, storage_key)` para el lote.
    :type page_batch_info: List[Tuple[int, str]]
    :param src_lang: Código del idioma de origen.
    :type src_lang: str
    :param tgt_lang: Código del idioma de destino.
    :type tgt_lang: str
    :param language_model: Modelo de IA a utilizar.
    :type language_model: str
    :param confidence: Umbral de confianza para la detección de layout.
    :type confidence: float
    :return: Una lista de diccionarios, cada uno conteniendo los datos procesados
             de una página (regiones de texto, imágenes, etc.).
    :rtype: List[Dict[str, Any]]
    """
    try:
        page_numbers = [info[0] for info in page_batch_info]
        logger.info(f"Procesando lote de páginas {page_numbers} para tarea {task_id}")
        
        page_images = [Image.open(BytesIO(download_bytes(key))).convert("RGB") for _, key in page_batch_info]
        extracted_data = extract_page_data_in_batch(page_images, confidence)
        translated_data = asyncio.run(translate_extracted_text(extracted_data, tgt_lang, language_model))

        final_batch_results = []
        for i, result in enumerate(translated_data):
            result["page_number"] = page_batch_info[i][0]
            result.setdefault("error", None)
            final_batch_results.append(result)
            
        logger.info(f"Batch pages {page_numbers} processed successfully (extraction + translation)")
        return final_batch_results
    
    except FlexibleChecksumError as e:
        logger.warning(f"Error de checksum en lote {page_numbers}. Reintentando... Error: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Fatal error processing page batch {page_numbers}: {e}", exc_info=True)
        error_results = [{
            "page_number": page_num, "text_regions": [], "image_regions": [],
            "page_dimensions": None, "error": f"Batch processing failed: {str(e)}",
        } for page_num, _ in page_batch_info]
        return error_results

@celery_app.task(name='assemble_final_pdf', bind=True)
def assemble_final_pdf(self, results_from_batches: List[List[Dict[str, Any]]], task_id: str, original_key: str, src_lang: str, tgt_lang: str):
    """Tarea finalizadora que ensambla el PDF completo a partir de los resultados de los lotes.

    Esta tarea se ejecuta una vez que todas las tareas `extract_and_translate_batch`
    de un `chord` han finalizado. Consolida los resultados, construye el PDF,
    genera y guarda los metadatos de traducción y posición.

    :param self: Instancia de la tarea de Celery.
    :param results_from_batches: Una lista de listas, donde cada sublista es el resultado
                                 de una tarea de procesamiento de lote.
    :type results_from_batches: List[List[Dict[str, Any]]]
    :param task_id: Identificador único de la tarea global.
    :type task_id: str
    :param original_key: Clave de S3 del PDF original.
    :type original_key: str
    :param src_lang: Código del idioma de origen.
    :type src_lang: str
    :param tgt_lang: Código del idioma de destino.
    :type tgt_lang: str
    :return: Un diccionario con el estado final y las claves de S3 de los artefactos generados.
    :rtype: dict
    """
    try:
        results_list = [item for sublist in results_from_batches for item in sublist]
        logger.info(f"Finalizing task {task_id} with {len(results_list)} pages from {len(results_from_batches)} batches.")
        results_list.sort(key=lambda r: r.get("page_number", 0))
        
        self.update_state(state='PROGRESS', meta={'status': 'Finalizando documento'})
        
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, tgt_lang)
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        translation_data = {
            "pages": [{
                "page_number": page_data.get('page_number', i),
                "translations": [{
                    "id": text_region["id"], "original_text": text_region["original_text"], "translated_text": text_region["translated_text"]
                } for text_region in page_data.get("text_regions", [])]
            } for i, page_data in enumerate(results_list) if not page_data.get("error")]
        }
        
        position_data = {
            "pages": [{
                "page_number": page_data.get('page_number', i), "dimensions": page_data.get("page_dimensions"),
                "regions": [{"id": text_region["id"], "position": text_region["position"]} for text_region in page_data.get("text_regions", [])],
                "image_regions": page_data.get("image_regions", [])
            } for i, page_data in enumerate(results_list) if not page_data.get("error")]
        }
        
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        
        upload_bytes(translation_key, json.dumps(translation_data, ensure_ascii=False, indent=2).encode(), "application/json")
        upload_bytes(position_key, json.dumps(position_data, ensure_ascii=False, indent=2).encode(), "application/json")
        
        errors = [r["error"] for r in results_list if r and r.get("error")]
        meta_data = {
            "pages": len(results_list), "errors": errors, "src_lang": src_lang, "tgt_lang": tgt_lang,
            "completed_at": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
        }
        meta_key = f"{task_id}/translated/metadata.json"
        upload_bytes(meta_key, json.dumps(meta_data, ensure_ascii=False, indent=2).encode(), "application/json")
        
        logger.info(f"Task {task_id} completed successfully")
        
        return {
            "status": "COMPLETED", "translated_key": translated_key,
            "translation_data_key": translation_key, "position_data_key": position_key,
            "meta_key": meta_key, "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Error finalizing task {task_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}

@celery_app.task(name='regenerate_pdf_from_storage')
def regenerate_pdf_from_storage(task_id: str, translation_data: dict, position_data: dict):
    """Regenera un PDF a partir de datos de traducción y posición almacenados.

    Esta tarea se utiliza cuando un usuario edita las traducciones a través de la
    interfaz. Recibe los textos actualizados y la información de layout original
    para reconstruir el PDF sin necesidad de un reprocesamiento completo (OCR, etc.).

    :param task_id: Identificador único de la tarea.
    :type task_id: str
    :param translation_data: Diccionario con los datos de texto (original y traducido).
    :type translation_data: dict
    :param position_data: Diccionario con la información de layout (posiciones, dimensiones).
    :type position_data: dict
    :return: Un diccionario indicando el éxito y la clave de S3 del nuevo PDF.
    :rtype: dict
    """
    try:
        logger.info(f"Regenerating PDF from storage for task {task_id}")
        
        tgt_lang = position_data.get("meta", {}).get("tgt_lang", "es")

        results_list = []
        for page in translation_data.get("pages", []):
            page_num = page["page_number"]
            page_pos = next((p for p in position_data.get("pages", []) if p["page_number"] == page_num), None)
            if not page_pos: continue

            dimensions = page_pos.get("dimensions", {"width": 595, "height": 842})
            
            text_regions = []
            for trans in page.get("translations", []):
                region_pos = next((r for r in page_pos.get("regions", []) if r["id"] == trans["id"]), None)
                if region_pos:
                    text_regions.append({
                        "id": trans["id"], "original_text": trans["original_text"],
                        "translated_text": trans["translated_text"], "position": region_pos["position"]
                    })
            
            results_list.append({
                "page_number": page_num, "page_dimensions": dimensions,
                "text_regions": text_regions, "image_regions": page_pos.get("image_regions", []),
                "error": None
            })
        
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, tgt_lang)
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        logger.info(f"PDF regenerated successfully for task {task_id}")
        return {"success": True, "translated_key": translated_key}
        
    except Exception as e:
        logger.error(f"Error regenerating PDF from storage for task {task_id}: {e}", exc_info=True)
        return {"error": str(e)}