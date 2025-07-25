# tasks.py

from celery import Celery, current_task, group, chord
import os
from pathlib import Path
import logging
import json
import tempfile

# Imports del proyecto
from src.domain.translator.processor import regenerate_pdf, extract_and_translate_page_data, get_font_for_language, adjust_paragraph_font_size
from src.domain.translator.pdf_utils import convert_pdf_to_images_and_save, cleanup_temp_directory
from src.infrastructure.config.settings import MARGIN

# Imports de terceros
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from PIL import Image
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

@celery_app.task(name='translate_pdf', bind=True)
def translate_pdf(self, pdf_path: str, task_id: str, target_language: str = "es", model_type: str = "primalayout"):
    """
    Tarea orquestadora que inicia el proceso de traducción paralela.
    """
    try:
        logger.info(f"Iniciando orquestación para la traducción del PDF {pdf_path} a {target_language}")
        
        # 1. Fase de Setup: Convertir PDF a imágenes
        temp_dir = tempfile.mkdtemp(prefix=f"pdf_task_{task_id}_")
        logger.info(f"Directorio temporal creado: {temp_dir}")
        
        self.update_state(state='PROGRESS', meta={'status': 'Convirtiendo PDF a imágenes...'})
        image_paths = convert_pdf_to_images_and_save(pdf_path, temp_dir=temp_dir)
        
        if not image_paths:
            raise Exception("No se pudieron generar imágenes del PDF.")
        
        total_pages = len(image_paths)
        logger.info(f"PDF convertido en {total_pages} páginas/imágenes.")

        # 2. Fase de "Map": Crear tareas paralelas para cada página
        # El callback (combine_pages_task) se ejecutará cuando todas las tareas del grupo terminen
        callback = combine_pages_task.s(
            task_id=task_id,
            target_language=target_language,
            temp_dir=temp_dir,
            image_paths=image_paths # Pasamos las rutas para el recorte de imágenes
        )
        
        # Creamos una tarea por cada página
        header = group(
            process_page_task.s(
                image_path=path,
                page_num=i,
                target_language=target_language,
                model_type=model_type,
            )
            for i, path in enumerate(image_paths)
        )
        
        # 3. Ejecutar el Chord
        # El chord es la combinación del grupo (header) y el callback
        # El resultado de esta llamada es un AsyncResult que representa el estado del callback
        chord_result = chord(header)(callback)

        logger.info(f"Chord iniciado. Tarea de combinación (callback) ID: {chord_result.id}")

        # La tarea orquestadora finaliza aquí. El cliente debe monitorear el chord_result.id
        # para obtener el resultado final.
        return {
            'status': 'PROCESSING',
            'message': f'Procesamiento en paralelo iniciado para {total_pages} páginas.',
            'result_task_id': chord_result.id # ID de la tarea de combinación
        }

    except Exception as e:
        logger.error(f"Error en la tarea de orquestación `translate_pdf`: {e}", exc_info=True)
        # Limpiar directorio si la orquestación falla
        if 'temp_dir' in locals() and temp_dir:
            cleanup_temp_directory(temp_dir)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}

@celery_app.task(name='process_page_task')
def process_page_task(image_path: str, page_num: int, target_language: str, model_type: str):
    """
    Tarea trabajadora: procesa una sola página (imagen).
    Realiza layout, OCR y traducción, y devuelve los datos estructurados.
    """
    logger.info(f"Procesando página {page_num+1} desde {image_path}")
    page_data = extract_and_translate_page_data(image_path, target_language, model_type)
    
    # Añadir el número de página al resultado para poder ordenarlo después
    page_data['page_number'] = page_num
    
    return page_data

@celery_app.task(name='combine_pages_task', bind=True)
def combine_pages_task(self, results: list, task_id: str, target_language: str, temp_dir: str, image_paths: list):
    """
    Tarea de agregación: se ejecuta después de que todas las páginas se procesan.
    Combina los resultados en un único PDF.
    """
    try:
        logger.info(f"Combinando resultados de {len(results)} páginas para la tarea {task_id}")
        
        # Ordenar los resultados por número de página
        sorted_results = sorted(results, key=lambda r: r.get('page_number', -1))
        
        # Setup del PDF final
        translated_dir = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
        translated_dir.mkdir(exist_ok=True)
        output_filename = f"{task_id}_translated.pdf"
        output_pdf_path = str(translated_dir / output_filename)
        
        pdf_canvas = canvas.Canvas(output_pdf_path)
        styles = getSampleStyleSheet()
        base_style = styles["Normal"]
        font_name = get_font_for_language(target_language)
        
        all_translation_data = []

        # Recorrer cada página procesada y dibujarla en el PDF
        for i, page_data in enumerate(sorted_results):
            self.update_state(state='PROGRESS', meta={'status': f'Ensamblando página {i+1}/{len(sorted_results)}...'})

            if page_data.get("error"):
                logger.warning(f"Saltando página {i+1} debido a un error de procesamiento: {page_data['error']}")
                continue

            dims = page_data["page_dimensions"]
            page_width, page_height = dims["width"], dims["height"]
            pdf_canvas.setPageSize((page_width, page_height))
            
            # Fondo blanco para cubrir cualquier artefacto de la imagen original
            pdf_canvas.setFillColorRGB(1, 1, 1)
            pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

            # Dibujar regiones de imagen
            page_image = Image.open(image_paths[i])
            for img_region in page_data.get("image_regions", []):
                coords = img_region["coordinates"]
                cropped_img = page_image.crop((
                    max(coords["x1"] - MARGIN, 0), max(coords["y1"] - MARGIN, 0),
                    min(coords["x2"] + MARGIN, page_image.width), min(coords["y2"] + MARGIN, page_image.height)
                ))
                img_byte_arr = io.BytesIO()
                cropped_img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                pos = img_region["position"]
                pdf_canvas.drawImage(ImageReader(img_byte_arr), pos["x"], pos["y"], pos["width"], pos["height"])

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
            all_translation_data.append(page_data)

        pdf_canvas.save()
        logger.info(f"PDF traducido guardado en: {output_pdf_path}")
        
        # Guardar datos de traducción y posición
        base_path = output_pdf_path.replace('.pdf', '')
        translation_data_path = f"{base_path}_translation_data.json"
        position_data_path = f"{base_path}_translation_data_position.json"
        
        # Construir datos de traducción en el formato esperado
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
                for i, page_data in enumerate(sorted_results) if not page_data.get("error")
            ]
        }
        
        # Construir datos de posición en el formato esperado
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
                    ]
                }
                for i, page_data in enumerate(sorted_results) if not page_data.get("error")
            ]
        }
        
        # Guardar archivos JSON
        with open(translation_data_path, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, ensure_ascii=False, indent=2)
        
        with open(position_data_path, 'w', encoding='utf-8') as f:
            json.dump(position_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Datos de traducción guardados en: {translation_data_path}")
        logger.info(f"Datos de posición guardados en: {position_data_path}")
        
        return {
            "status": "completed",
            "output_path": output_pdf_path,
        }
    except Exception as e:
        logger.error(f"Error en la tarea de combinación `combine_pages_task`: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        return {"status": "failed", "error": str(e)}
    finally:
        # Limpiar directorio temporal sin importar si hubo éxito o fallo
        logger.info(f"Limpiando directorio temporal: {temp_dir}")
        cleanup_temp_directory(temp_dir)


@celery_app.task(name='regenerate_pdf')
def regenerate_pdf_task(task_id: str, translation_data: dict, position_data: dict):
    try:
        logger.info(f"Starting PDF regeneration for task {task_id}")
        
        # Get directories
        translated_dir = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
        translated_dir.mkdir(exist_ok=True)
        
        # Get paths
        output_filename = f"{task_id}_translated.pdf"
        output_pdf_path = str(translated_dir / output_filename)
        
        # Get target language from translation data file
        translation_data_path = output_pdf_path.replace('.pdf', '_translation_data.json')
        with open(translation_data_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            # Get first translation from first page to check target language
            first_page = old_data.get("pages", [])[0] if "pages" in old_data else None
            first_translation = first_page.get("translations", [])[0] if first_page else None
            target_language = first_translation.get("target_language", "es") if first_translation else "es"
        
        # Regenerate PDF
        result = regenerate_pdf(
            output_pdf_path=output_pdf_path,
            translation_data=translation_data,
            position_data=position_data,
            target_language=target_language
        )
        
        if "error" in result:
            logger.error(f"Error regenerating PDF: {result['error']}")
            return result
            
        logger.info("PDF regeneration completed successfully")
        return {
            "success": True,
            "output_path": output_pdf_path
        }
    except Exception as e:
        logger.error(f"Unexpected error in regeneration task: {str(e)}")
        return {
            "error": str(e)
        }