import pytesseract
from PIL import Image
import logging
from pytesseract import Output
from typing import List,Tuple


def extract_text_from_image(image: Image.Image) -> str:
    """
    Extrae texto de una imagen utilizando OCR.

    Args:
        image (Image.Image): Imagen de la cual extraer el texto.

    Returns:
        str: Texto extraído.
    """
    try:
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception as e:
        logging.error(f"Error al extraer texto de la imagen: {e}")
        return ""

def extract_text_with_boxes_from_image(image: Image.Image, confidence_threshold: int = 60) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """
    Extrae texto y sus correspondientes cajas delimitadoras (bounding boxes) de una imagen.
    
    Args:
        image (Image.Image): La imagen de la cual extraer los datos.
        confidence_threshold (int): El umbral de confianza (0-100) para incluir una palabra.
                                    Las detecciones por debajo de este valor se ignorarán.
    Returns:
        List[Tuple[str, Tuple[int, int, int, int]]]: 
        Una lista de tuplas, donde cada tupla contiene:
        - El texto de la palabra detectada (str).
        - Las coordenadas de su caja en formato (x1, y1, x2, y2) (Tuple[int, int, int, int]).
    """
    results = []
    try:
        # Usamos image_to_data para obtener información detallada.
        # Output.DICT formatea la salida como un diccionario fácil de usar.
        data = pytesseract.image_to_data(image, output_type=Output.DICT)
        
        num_boxes = len(data['level'])
        for i in range(num_boxes):
            # Solo consideramos palabras con una confianza superior al umbral.
            # Tesseract devuelve -1 para cajas que agrupan varias palabras, las ignoramos aquí.
            conf = int(data['conf'][i])
            if conf > confidence_threshold:
                text = data['text'][i]
                # Asegurarnos de que no es una cadena vacía o solo espacios
                if text and text.strip():
                    # Coordenadas que proporciona Tesseract
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # Creamos la caja en formato (x1, y1, x2, y2)
                    box = (x, y, x + w, y + h)
                    results.append((text.strip(), box))
                    
        return results
    except Exception as e:
        logging.error(f"Error al extraer texto con cajas de la imagen: {e}", exc_info=True)
        return []