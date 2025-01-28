from celery import Celery, current_task
import os
from pathlib import Path
import logging
import json
from src.domain.translator.processor import process_pdf, regenerate_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

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

@celery_app.task(name='translate_pdf')
def translate_pdf(task_id: str = None, pdf_path: str = None, target_language: str = "es", model_type: str = "primalayout"):
    try:
        logger.info(f"Starting translation of PDF {pdf_path} to {target_language}")
        
        # Get directories from environment variables or use defaults
        translated_dir = Path(os.getenv('TRANSLATED_FOLDER', '/app/translated'))
        translated_dir.mkdir(exist_ok=True)
        
        # Define output path
        output_filename = f"{task_id}_translated.pdf"
        output_pdf_path = str(translated_dir / output_filename)
        
        def update_progress(current: int, total: int):
            progress = {
                'current': current,
                'total': total,
                'percent': int((current / total) * 100)
            }
            current_task.update_state(
                state='PROGRESS',
                meta=progress
            )
            logger.info(f"Processing page {current} of {total}")

        # Process the PDF
        result = process_pdf(
            pdf_path=pdf_path,
            output_pdf_path=output_pdf_path,
            target_language=target_language,
            progress_callback=update_progress,
            model_type=model_type
        )
        
        if "error" in result:
            logger.error(f"Error processing PDF: {result['error']}")
            return {
                "status": "failed",
                "error": result["error"]
            }
            
        logger.info(f"PDF translation completed successfully")
        logger.info(f"Result from process_pdf: {result}")
        return {
            "status": "completed",
            "output_path": output_pdf_path,
            "translation_data_path": result.get("translation_data_path")
        }
    except Exception as e:
        logger.error(f"Unexpected error in translation task: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
