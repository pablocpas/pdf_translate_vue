# tasks.py - PDF Translation Worker Tasks
# 
# WORKFLOW:
# 1. process_pdf_document: Orchestrates the entire translation process
# 2. extract_and_translate_batch: Processes page batches (layout detection + OCR + translation)
# 3. assemble_final_pdf: Combines all results into final PDF
# 4. regenerate_pdf_from_storage: Regenerates PDF from stored translation data

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

import asyncio


from src.domain.translator.translator import translate_text_async
from reportlab.lib.utils import ImageReader

# Imports del proyecto
# ¡IMPORTANTE! Cambiamos el import a nuestra nueva función de batching
from src.domain.translator.processor import extract_page_data_in_batch
from src.domain.translator.utils import get_font_for_language, adjust_paragraph_font_size
from src.infrastructure.config.settings import MARGIN, settings
from src.infrastructure.storage.s3 import upload_bytes, download_bytes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

PAGE_PROCESSING_BATCH_SIZE = 16


# =============================================================================
# PDF CONSTRUCTION UTILITIES
# =============================================================================
def build_translated_pdf(results_list: List[Dict[str, Any]], task_id: str, target_language: str) -> bytes:
    """
    Constructs the final PDF from processed page results.
    
    Args:
        results_list: List of page processing results with text/image regions
        task_id: Unique task identifier for S3 storage keys
        target_language: Target language code for font selection
    
    Returns:
        bytes: Complete PDF document as bytes
    """
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer)
    styles = getSampleStyleSheet()
    base_style = styles["Normal"]
    font_name = get_font_for_language(target_language)
    
    for i, page_data in enumerate(results_list):
        if page_data.get("error"):
            logger.warning(f"Saltando página {i+1} debido a error: {page_data['error']}")
            continue

        if not page_data.get("page_dimensions"):
            logger.warning(f"Saltando página {i+1} por falta de dimensiones.")
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
# CELERY TASK DEFINITIONS
# =============================================================================

# MAIN ORCHESTRATOR TASK

@celery_app.task(name='process_pdf_document', bind=True)
def process_pdf_document(self, file_content: bytes, src_lang: str, tgt_lang: str, language_model: str = "openai/gpt-4o-mini", confidence: float = 0.45):
    """
    Main orchestrator task: Converts PDF to images, creates batches,
    and launches parallel batch processing tasks.
    
    WORKFLOW:
    1. Upload original PDF to storage
    2. Convert PDF pages to images
    3. Create processing batches
    4. Launch parallel batch processing via Celery chord
    
    Args:
        file_content: PDF file as bytes
        src_lang: Source language code
        tgt_lang: Target language code
        language_model: AI model for translation
        confidence: Layout detection confidence threshold
    
    Returns:
        dict: Task status and result task ID
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


# TRANSLATION PIPELINE

async def translate_extracted_text(extracted_data: List[Dict[str, Any]], tgt_lang: str, language_model: str) -> List[Dict[str, Any]]:
    """
    Manages concurrent translation API calls for a batch of pages.
    
    Args:
        extracted_data: List of page data with extracted text regions
        tgt_lang: Target language code
        language_model: AI model identifier
    
    Returns:
        List[Dict]: Same data structure with translated_text added to regions
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
        
        # Fallback en caso de que la API no devuelva el número correcto de traducciones
        if len(translated_texts) == len(text_regions):
            for j, region in enumerate(text_regions):
                region["translated_text"] = translated_texts[j]
        else:
            logger.warning(f"Discrepancia de traducción en página del lote {i}. Se usará texto original.")
            for region in text_regions:
                region["translated_text"] = region["original_text"]
    
    return extracted_data



# BATCH PROCESSING TASK

@celery_app.task(
    name='extract_and_translate_batch', 
    bind=True,
    autoretry_for=(FlexibleChecksumError,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60
)
def extract_and_translate_batch(self, task_id: str, page_batch_info: List[Tuple[int, str]], src_lang: str, tgt_lang: str, language_model: str, confidence: float):
    """
    Worker task: Processes a BATCH of pages performing layout detection, OCR, and translation.
    
    PROCESS:
    1. Download page images from storage
    2. Perform layout detection and OCR (batch processing)
    3. Translate extracted text via API
    4. Return structured page data with translations
    
    Args:
        task_id: Unique task identifier
        page_batch_info: List of (page_number, storage_key) tuples
        src_lang: Source language code
        tgt_lang: Target language code  
        language_model: AI model for translation
        confidence: Layout detection confidence
    
    Returns:
        List[Dict]: Processed page data with text/image regions
    """
    try:
        page_numbers = [info[0] for info in page_batch_info]
        logger.info(f"Procesando lote de páginas {page_numbers} para tarea {task_id}")
        
        # Step 1: Download batch images from storage
        page_images = [Image.open(BytesIO(download_bytes(key))).convert("RGB") for _, key in page_batch_info]
        
        # Step 2: Extract data (layout detection + OCR) using batch processing
        extracted_data = extract_page_data_in_batch(page_images, confidence)
        
        # Step 3: Translate all extracted text
        translated_data = asyncio.run(translate_extracted_text(extracted_data, tgt_lang, language_model))

        # Step 4: Assign page numbers to results
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


# PDF ASSEMBLY TASK

@celery_app.task(name='assemble_final_pdf', bind=True)
def assemble_final_pdf(self, results_from_batches: List[List[Dict[str, Any]]], task_id: str, original_key: str, src_lang: str, tgt_lang: str):
    """
    Finalizer task: Assembles the complete PDF from batch results and uploads to storage.
    
    PROCESS:
    1. Flatten and sort all batch results by page number
    2. Build final PDF with translated text and preserved layout
    3. Generate translation and position metadata
    4. Upload all files to storage
    
    Args:
        results_from_batches: Nested list of batch processing results
        task_id: Unique task identifier
        original_key: Storage key for original PDF
        src_lang: Source language code
        tgt_lang: Target language code
    
    Returns:
        dict: Completion status and storage keys
    """
    try:
        # Flatten and sort batch results by page number
        results_list = [item for sublist in results_from_batches for item in sublist]
        logger.info(f"Finalizing task {task_id} with {len(results_list)} pages from {len(results_from_batches)} batches.")
        
        results_list.sort(key=lambda r: r.get("page_number", 0))
        
        self.update_state(state='PROGRESS', meta={'status': 'Finalizando documento'})
        
        # Build the final PDF with translations
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, tgt_lang)
        
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        # Build and upload translation metadata
        translation_data = {
            "pages": [{
                "page_number": page_data.get('page_number', i),
                "translations": [{
                    "id": text_region["id"],
                    "original_text": text_region["original_text"],
                    "translated_text": text_region["translated_text"]
                } for text_region in page_data.get("text_regions", [])]
            } for i, page_data in enumerate(results_list) if not page_data.get("error")]
        }
        
        position_data = {
            "pages": [{
                "page_number": page_data.get('page_number', i),
                "dimensions": page_data.get("page_dimensions"),
                "regions": [{
                    "id": text_region["id"],
                    "position": text_region["position"]
                } for text_region in page_data.get("text_regions", [])],
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
            "status": "COMPLETED",
            "translated_key": translated_key,
            "translation_data_key": translation_key,
            "position_data_key": position_key,
            "meta_key": meta_key,
            "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Error finalizing task {task_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}


# PDF REGENERATION TASK

@celery_app.task(name='regenerate_pdf_from_storage')
def regenerate_pdf_from_storage(task_id: str, translation_data: dict, position_data: dict):
    """
    Regenerates PDF from stored translation data with updated translations.
    
    Used for editing translations without re-processing the entire document.
    
    Args:
        task_id: Unique task identifier
        translation_data: Dictionary with translation text data
        position_data: Dictionary with layout positions and dimensions
    
    Returns:
        dict: Success status and storage key
    """
    try:
        logger.info(f"Regenerating PDF from storage for task {task_id}")
        
        # Determinar idioma de destino
        tgt_lang = "es" # Default
        if position_data.get("meta", {}).get("tgt_lang"):
             tgt_lang = position_data["meta"]["tgt_lang"]

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
                        "id": trans["id"],
                        "original_text": trans["original_text"],
                        "translated_text": trans["translated_text"],
                        "position": region_pos["position"]
                    })
            
            results_list.append({
                "page_number": page_num,
                "page_dimensions": dimensions,
                "text_regions": text_regions,
                "image_regions": page_pos.get("image_regions", []),
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