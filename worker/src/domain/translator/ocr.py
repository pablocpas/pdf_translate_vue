import pytesseract
from PIL import Image
import logging

def extract_text_from_image(image: Image.Image) -> str:
    """Extrae texto de una imagen usando OCR"""
    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logging.error(f"Error al extraer texto de la imagen: {e}")
        return ""
