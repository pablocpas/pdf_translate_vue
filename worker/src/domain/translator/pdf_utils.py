"""Utilidades para el manejo de archivos PDF y sus representaciones como imágenes.

Este módulo contiene funciones auxiliares para tareas relacionadas con PDFs,
como calcular las dimensiones de una página en puntos a partir de su imagen.
"""
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)

def get_page_dimensions_from_image(image_path: str, dpi: int = 300) -> Tuple[float, float]:
    """Calcula las dimensiones de una página en puntos (points) a partir de una imagen.

    Las dimensiones en PDF se miden en puntos (1 pulgada = 72 puntos). Esta función
    convierte las dimensiones en píxeles de una imagen a puntos, basándose en los
    DPI (puntos por pulgada) con los que se renderizó la imagen.

    :param image_path: La ruta al archivo de imagen de la página.
    :type image_path: str
    :param dpi: Los DPI utilizados para crear la imagen desde el PDF.
    :type dpi: int
    :return: Una tupla `(ancho, alto)` en puntos.
    :rtype: Tuple[float, float]
    :raises Exception: Si no se puede abrir o procesar la imagen.
    """
    try:
        with Image.open(image_path) as img:
            width_px, height_px = img.size
            width_pts = (width_px * 72.0) / dpi
            height_pts = (height_px * 72.0) / dpi
            return width_pts, height_pts
    except Exception as e:
        logger.error(f"Error al obtener dimensiones de {image_path}: {e}")
        raise