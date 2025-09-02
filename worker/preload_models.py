# preload_models.py - Precarga de modelos y librerías pesadas

import logging
import time
import sys
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Cache global para modelos precargados
_MODEL_CACHE: Dict[str, Any] = {}

def preload_heavy_imports():
    """
    Precarga todas las librerías pesadas que se usan en el worker.
    Esto se ejecuta una sola vez al iniciar el worker.
    """
    logger.info("🚀 Iniciando precarga de librerías pesadas...")
    start_time = time.time()
    
    try:
        # 1. Precarga de librerías de ML/CV más lentas
        logger.info("📦 Precargando doclayout_yolo...")
        from doclayout_yolo import YOLOv10
        
        logger.info("📦 Precargando shapely...")
        from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
        from shapely.ops import unary_union
        
        logger.info("📦 Precargando PIL/Pillow...")
        from PIL import Image, ImageDraw, ImageFont
        
        logger.info("📦 Precargando pytesseract...")
        import pytesseract
        
        logger.info("📦 Precargando pdf2image...")
        from pdf2image import convert_from_bytes, convert_from_path
        
        logger.info("📦 Precargando reportlab...")
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph
        from reportlab.lib.utils import ImageReader
        
        logger.info("📦 Precargando numpy...")
        import numpy as np
        
        # 2. Precargar y cachear el modelo YOLOv10
        logger.info("🤖 Precargando modelo YOLOv10...")
        from src.domain.translator.layout import LayoutModel
        model = LayoutModel("yolov10_doc")
        _MODEL_CACHE["yolo_model"] = model
        logger.info("✅ Modelo YOLOv10 precargado y cacheado")
        
        # 3. Precarga de módulos del proyecto
        logger.info("📦 Precargando módulos del proyecto...")
        from src.domain.translator.processor import extract_and_translate_page_data
        from src.domain.translator.ocr import extract_text_from_image  
        from src.infrastructure.config.settings import settings
        
        total_time = time.time() - start_time
        logger.info(f"✅ Precarga completada en {total_time:.2f} segundos")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la precarga: {e}")
        return False

def get_cached_model(model_name: str) -> Any:
    """
    Obtiene un modelo desde el cache. Si no existe, lo carga.
    """
    if model_name not in _MODEL_CACHE:
        if model_name == "yolo_model":
            from src.domain.translator.layout import LayoutModel
            _MODEL_CACHE[model_name] = LayoutModel("yolov10_doc")
        else:
            raise ValueError(f"Modelo {model_name} no soportado")
    
    return _MODEL_CACHE[model_name]

def warm_up_models():
    """
    Ejecuta una pasada de calentamiento con los modelos para inicializar
    cualquier caché interno o compilación JIT.
    """
    logger.info("🔥 Iniciando calentamiento de modelos...")
    start_time = time.time()
    
    try:
        # Crear una imagen dummy pequeña para test
        from PIL import Image
        import numpy as np
        
        dummy_image = Image.fromarray(
            np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        )
        
        # Calentar YOLOv10
        yolo_model = get_cached_model("yolo_model")
        _ = yolo_model.get_model().predict(source=dummy_image, conf=0.5, device="cpu")
        
        warm_time = time.time() - start_time
        logger.info(f"🔥 Calentamiento completado en {warm_time:.2f} segundos")
        
    except Exception as e:
        logger.warning(f"⚠️ Error durante calentamiento (no crítico): {e}")