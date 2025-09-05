"""Módulo de Reconocimiento Óptico de Caracteres (OCR).

Proporciona una función simple para extraer texto de una imagen utilizando
la biblioteca Tesseract a través de su wrapper `pytesseract`.
"""
import pytesseract
from PIL import Image
import logging

def extract_text_from_image(image: Image.Image) -> str:
    """Extrae texto de un objeto de imagen utilizando Tesseract OCR.

    :param image: El objeto `PIL.Image` del cual se extraerá el texto.
    :type image: Image.Image
    :return: El texto extraído como una cadena. Devuelve una cadena vacía si
             ocurre un error.
    :rtype: str
    """
    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logging.error(f"Error al extraer texto de la imagen: {e}")
        return ""