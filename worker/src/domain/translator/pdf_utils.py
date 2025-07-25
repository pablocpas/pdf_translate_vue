"""
Utilidades para el manejo de PDFs y conversión a imágenes.
Optimizado para procesamiento paralelo de páginas.
"""
import os
import logging
import tempfile
import uuid
from pathlib import Path
from typing import List, Tuple
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


def convert_pdf_to_images_and_save(
    pdf_path: str, 
    temp_dir: str = None,
    dpi: int = 300
) -> List[str]:
    """
    Convierte un PDF a imágenes y las guarda en archivos temporales.
    
    Esta función está optimizada para el procesamiento paralelo:
    - Convierte todas las páginas de una vez (más eficiente que página por página)
    - Guarda cada imagen en un archivo temporal para procesamiento independiente
    - Retorna las rutas a los archivos de imagen para procesamiento paralelo
    
    Args:
        pdf_path (str): Ruta al archivo PDF original
        temp_dir (str): Directorio temporal. Si es None, usa el directorio temporal del sistema
        dpi (int): Resolución para la conversión (default: 300)
    
    Returns:
        List[str]: Lista de rutas a los archivos de imagen temporales
        
    Raises:
        Exception: Si hay errores en la conversión del PDF
    """
    try:
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="pdf_processing_")
        else:
            Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Convirtiendo PDF a imágenes con DPI={dpi}")
        
        # Conversión única de todo el PDF (más eficiente)
        page_images = convert_from_path(pdf_path, dpi=dpi)
        
        logger.info(f"PDF convertido exitosamente. Total de páginas: {len(page_images)}")
        
        # Guardar cada imagen en un archivo temporal
        image_paths = []
        for i, page_image in enumerate(page_images):
            # Generar nombre único para evitar conflictos
            image_filename = f"page_{i:03d}_{uuid.uuid4().hex[:8]}.png"
            image_path = os.path.join(temp_dir, image_filename)
            
            # Guardar imagen como PNG para preservar calidad
            page_image.save(image_path, "PNG", optimize=True)
            image_paths.append(image_path)
            
            logger.debug(f"Página {i+1} guardada en: {image_path}")
        
        logger.info(f"Todas las imágenes guardadas en: {temp_dir}")
        return image_paths
        
    except Exception as e:
        logger.error(f"Error al convertir PDF a imágenes: {e}")
        raise


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


def save_image_region_to_temp_file(image_data: Image.Image, temp_dir: str = None) -> str:
    """
    Guarda una región de imagen en un archivo temporal.
    
    Args:
        image_data (Image.Image): Datos de la imagen PIL
        temp_dir (str): Directorio temporal
        
    Returns:
        str: Ruta al archivo temporal guardado
    """
    try:
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        
        # Generar nombre único
        filename = f"image_region_{uuid.uuid4().hex[:8]}.png"
        temp_path = os.path.join(temp_dir, filename)
        
        # Guardar imagen
        image_data.save(temp_path, "PNG", optimize=True)
        return temp_path
        
    except Exception as e:
        logger.error(f"Error al guardar región de imagen: {e}")
        raise


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Limpia archivos temporales de forma segura.
    
    Args:
        file_paths (List[str]): Lista de rutas a archivos temporales para eliminar
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Archivo temporal eliminado: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo temporal {file_path}: {e}")


def cleanup_temp_directory(temp_dir: str) -> None:
    """
    Limpia un directorio temporal completo.
    
    Args:
        temp_dir (str): Directorio temporal a eliminar
    """
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Directorio temporal eliminado: {temp_dir}")
    except Exception as e:
        logger.warning(f"No se pudo eliminar directorio temporal {temp_dir}: {e}")