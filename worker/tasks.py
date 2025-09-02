# tasks.py - Refactorizado para arquitectura "Todo en Uno"
from celery.signals import worker_process_init
from src.domain.translator.layout import initialize_layout_model
from celery import Celery
import os
import logging
import json
import time
import asyncio
from typing import List, Dict, Any
from io import BytesIO



# Imports del proyecto
from src.domain.translator.processor import extract_and_translate_page_data, get_layout_in_batch, get_font_for_language, adjust_paragraph_font_size
from src.infrastructure.config.settings import MARGIN, settings
from src.infrastructure.storage.s3 import upload_bytes, download_bytes, presigned_get_url
from src.domain.translator.pdf_utils import get_page_dimensions_from_image

# Imports de terceros
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from PIL import Image
from pdf2image import convert_from_bytes
import io

# Configure logging
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

@worker_process_init.connect(sender=None)
def on_worker_init(**kwargs):
    """
    Esta función se ejecuta automáticamente UNA VEZ por cada proceso worker
    cuando arranca.
    """
    logger.info("Señal 'worker_process_init' recibida. Inicializando modelos...")
    initialize_layout_model()
    logger.info("Modelos inicializados correctamente para este worker.")


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

@celery_app.task(name='translate_pdf_task', bind=True)
async def translate_pdf_task(self, file_content: bytes, src_lang: str, tgt_lang: str, language_model: str = "openai/gpt-4o-mini", confidence: float = 0.45):
    """
    Tarea monolítica "Todo en Uno" que procesa un PDF completo con optimizaciones de batching y async I/O.
    """
    try:
        task_id = self.request.id
        logger.info(f"Iniciando procesamiento completo para tarea {task_id} -> {tgt_lang}")
        
        # 1. Preparación: subir PDF original y convertir a imágenes
        self.update_state(state='PROGRESS', meta={'status': 'Preparando documento'})
        original_key = f"{task_id}/original.pdf"
        upload_bytes(original_key, file_content, content_type="application/pdf")
        logger.info(f"PDF subido a S3: {original_key}")
        
        self.update_state(state='PROGRESS', meta={'status': 'Convirtiendo páginas a imágenes'})
        start_pdf_conversion = time.time()
        images = convert_from_bytes(file_content, fmt="png", dpi=300)
        pdf_conversion_time = time.time() - start_pdf_conversion
        
        if not images:
            raise Exception("No se pudieron generar imágenes del PDF.")
        
        logger.info(f"PDF convertido a {len(images)} imágenes en {pdf_conversion_time:.3f}s")
        
        # 2. Subir imágenes a S3 para referencia posterior
        page_keys = []
        for idx, img in enumerate(images):
            buf = BytesIO()
            img.save(buf, format="PNG")
            png_key = f"{task_id}/pages/page_{idx:03d}.png"
            upload_bytes(png_key, buf.getvalue(), content_type="image/png")
            page_keys.append(png_key)
        
        # 3. Inferencia de layout en lote (optimización clave)
        self.update_state(state='PROGRESS', meta={'status': 'Analizando estructura del documento'})
        start_batch_layout = time.time()
        batch_layouts = get_layout_in_batch(images, confidence=confidence, batch_size=8)
        batch_layout_time = time.time() - start_batch_layout
        logger.info(f"Layout batch processing completado en {batch_layout_time:.3f}s para {len(images)} páginas")
        
        # 4. Obtener dimensiones de cada página
        page_dimensions = []
        for idx, img in enumerate(images):
            # Simular archivo temporal para get_page_dimensions_from_image
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            
            # Usar las dimensiones de la imagen directamente (más eficiente)
            width_pts = img.width * 72 / 300  # DPI conversion
            height_pts = img.height * 72 / 300
            page_dimensions.append((width_pts, height_pts))
        
        # 5. Procesamiento concurrente de páginas (async I/O para traducciones)
        self.update_state(state='PROGRESS', meta={'status': 'Traduciendo contenido'})
        start_concurrent = time.time()
        
        # Crear corrutinas para cada página
        translation_coroutines = []
        for idx, (img, layout) in enumerate(zip(images, batch_layouts)):
            width_pts, height_pts = page_dimensions[idx]
            coro = extract_and_translate_page_data(
                img, layout, tgt_lang, language_model, width_pts, height_pts
            )
            translation_coroutines.append(coro)
        
        # Ejecutar todas las traducciones concurrentemente
        results_list = await asyncio.gather(*translation_coroutines)
        concurrent_time = time.time() - start_concurrent
        logger.info(f"Procesamiento concurrente completado en {concurrent_time:.3f}s")
        
        # 6. Agregar números de página a los resultados
        for idx, result in enumerate(results_list):
            result["page_number"] = idx
            if "error" not in result:
                result["error"] = None
        
        # 7. Finalización: construir PDF final
        self.update_state(state='PROGRESS', meta={'status': 'Finalizando documento'})
        start_pdf_build = time.time()
        translated_pdf_bytes = build_translated_pdf(results_list, task_id, tgt_lang)
        pdf_build_time = time.time() - start_pdf_build
        
        # 8. Subir PDF traducido a S3
        translated_key = f"{task_id}/translated/translated.pdf"
        upload_bytes(translated_key, translated_pdf_bytes, content_type="application/pdf")
        
        # 9. Construir y subir metadatos
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
        
        # 10. Subir metadatos a S3
        translation_key = f"{task_id}/translated/translated_translation_data.json"
        position_key = f"{task_id}/translated/translated_translation_data_position.json"
        
        upload_bytes(translation_key, json.dumps(translation_data, ensure_ascii=False, indent=2).encode(), "application/json")
        upload_bytes(position_key, json.dumps(position_data, ensure_ascii=False, indent=2).encode(), "application/json")
        
        # 11. Generar metadatos de resultado
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
        
        # Timing summary
        total_time = pdf_conversion_time + batch_layout_time + concurrent_time + pdf_build_time
        logger.info(f"=== COMPLETE TASK TIMING SUMMARY ===")
        logger.info(f"PDF conversion: {pdf_conversion_time:.3f}s")
        logger.info(f"Batch layout: {batch_layout_time:.3f}s")
        logger.info(f"Concurrent processing: {concurrent_time:.3f}s")
        logger.info(f"PDF reconstruction: {pdf_build_time:.3f}s")
        logger.info(f"Total processing time: {total_time:.3f}s")
        logger.info("=" * 40)
        
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
        logger.error(f"Error en tarea monolítica {task_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}






@celery_app.task(name='regenerate_pdf_s3')
def regenerate_pdf_s3_task(task_id: str, translation_data: dict, position_data: dict):
    """
    Regenera PDF desde S3 con nuevos datos de traducción.
    """
    try:
        logger.info(f"Regenerando PDF desde S3 para tarea {task_id}")
        
        # Procesar metadatos
        
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