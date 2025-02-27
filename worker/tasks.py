from celery import Celery, current_task
import os
from pathlib import Path
import logging
import json
from src.domain.translator.processor import process_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'pdf_translator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

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
        return {
            "status": "completed",
            "output_path": output_pdf_path
        }
    except Exception as e:
        logger.error(f"Unexpected error in translation task: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
