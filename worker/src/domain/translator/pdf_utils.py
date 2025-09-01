"""
Utilidades para el manejo de PDFs"""
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)


def get_page_dimensions_from_image(image_path: str, dpi: int = 300) -> Tuple[float, float]:
    """
    Calcula las dimensiones de una página en puntos basándose en la imagen.
    
    Args:
        image_path (str): Ruta al archivo de imagen
        dpi (int): DPI usado en la conversión original
        
    Returns:
        Tuple[float, float]: (ancho_pts, alto_pts) - Dimensiones en puntos
    """
    try:
        with Image.open(image_path) as img:
            width_px, height_px = img.size
            # Convertir píxeles a puntos (1 punto = 1/72 pulgadas)
            width_pts = (width_px * 72.0) / dpi
            height_pts = (height_px * 72.0) / dpi
            return width_pts, height_pts
    except Exception as e:
        logger.error(f"Error al obtener dimensiones de {image_path}: {e}")
        raise


# Removed obsolete functions: save_image_region_to_temp_file, cleanup_temp_files, cleanup_temp_directory
# These are no longer needed with S3 storage