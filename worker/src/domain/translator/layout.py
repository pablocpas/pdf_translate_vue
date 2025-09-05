"""Módulo de análisis de layout de documentos.

Este archivo contiene la lógica para detectar la estructura de una página
(párrafos, títulos, imágenes, tablas, etc.) utilizando un modelo YOLOv10.
Proporciona una clase singleton para cargar el modelo eficientemente y
una función optimizada para procesar imágenes en lote.
"""
import logging
import os
from typing import List, Tuple, NamedTuple
from PIL import Image

from doclayout_yolo import YOLOv10

logger = logging.getLogger(__name__)

# Estructuras de datos para el layout
class Rectangle(NamedTuple):
    """Representa un cuadro delimitador con coordenadas (x1, y1, x2, y2)."""
    x_1: float
    y_1: float
    x_2: float
    y_2: float

class LayoutElement(NamedTuple):
    """Representa un elemento detectado en el layout del documento.

    :param box: El cuadro delimitador del elemento.
    :type box: Rectangle
    :param type: El tipo de elemento (ej. 'TextRegion', 'ImageRegion').
    :type type: str
    :param score: La puntuación de confianza de la detección.
    :type score: float
    """
    box: Rectangle
    type: str
    score: float

# Configuración del modelo YOLOv10
YOLO_LABEL_MAP = {
    'plain text': 'TextRegion',
    'title': 'TextRegion',
    'list': 'TextRegion',
    'table': 'ImageRegion',
    'figure': 'ImageRegion',
    'section-header': 'TextRegion',
    'figure_caption': 'TextRegion',
    'table_caption': 'TextRegion',
    'table_footnote': 'TextRegion',
    'isolate_formula': 'ImageRegion',
    'formula_caption': 'TextRegion',
    'abandon': 'ImageRegion',
}

YOLO_MODEL_CONFIG = {
    "yolov10_doc": {
        "local_path": "/app/models/doclayout_yolo_docstructbench_imgsz1024.pt"
    }
}

class LayoutModel:
    """Clase singleton para gestionar la carga y acceso al modelo YOLOv10.

    Asegura que el modelo se cargue una sola vez en memoria, optimizando
    el uso de recursos.
    """
    _instances = {}

    def __new__(cls, model_type="yolov10_doc"):
        """Implementa el patrón singleton para la instancia del modelo."""
        if model_type not in cls._instances:
            instance = super(LayoutModel, cls).__new__(cls)
            instance._initialize_model(model_type)
            cls._instances[model_type] = instance
        return cls._instances[model_type]

    def _initialize_model(self, model_type):
        """Inicializa el modelo YOLOv10 desde un archivo local."""
        try:
            config = YOLO_MODEL_CONFIG.get(model_type, YOLO_MODEL_CONFIG["yolov10_doc"])
            local_path = config['local_path']
            
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"El modelo no se encuentra en {local_path}. Verificar la imagen Docker.")
            
            logger.info(f"Cargando modelo {model_type} desde: {local_path}")
            self.model = YOLOv10(local_path)
            self.model_type = model_type
            logger.info(f"Modelo {model_type} cargado correctamente.")
            
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo YOLOv10 cargado."""
        return self.model

def get_layouts_in_batch(images: List[Image.Image], model_type="yolov10_doc", confidence: float = 0.45, batch_size: int = 16) -> List[List[LayoutElement]]:
    """Obtiene el layout para una lista de imágenes usando inferencia por lotes.

    Esta función es una optimización clave, ya que procesa múltiples imágenes en
    una sola llamada al modelo, reduciendo la sobrecarga y acelerando el
    proceso de detección.

    :param images: Lista de objetos `PIL.Image` a procesar.
    :type images: List[Image.Image]
    :param model_type: El tipo de modelo a cargar (definido en `YOLO_MODEL_CONFIG`).
    :type model_type: str
    :param confidence: Umbral de confianza para filtrar las detecciones.
    :type confidence: float
    :param batch_size: Número de imágenes a procesar en cada lote de inferencia.
    :type batch_size: int
    :return: Una lista de layouts. Cada layout es, a su vez, una lista de `LayoutElement`.
    :rtype: List[List[LayoutElement]]
    """
    if not images:
        return []

    try:
        model = LayoutModel(model_type).get_model()
        
        det_results_batch = model.predict(source=images, conf=confidence, device="cpu", batch=batch_size)

        all_layouts = []
        if not det_results_batch:
            return [[] for _ in images]

        for detections in det_results_batch:
            layout = []
            for det in detections.boxes.data:
                x1, y1, x2, y2, score, class_id = det.tolist()
                class_name = detections.names[int(class_id)]
                region_type = YOLO_LABEL_MAP.get(class_name)
                
                if region_type:
                    layout.append(LayoutElement(
                        box=Rectangle(x_1=x1, y_1=y1, x_2=x2, y_2=y2),
                        type=region_type,
                        score=score
                    ))
            all_layouts.append(layout)
        
        return all_layouts
    except Exception as e:
        logger.error(f"Error al obtener el layout en lote: {e}", exc_info=True)
        return [[] for _ in images]

def merge_overlapping_text_regions(layout: List[LayoutElement]) -> Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]:
    """Separa los elementos de un layout en regiones de texto y de imagen.

    Actualmente, no realiza una fusión de regiones, simplemente clasifica los
    elementos detectados en dos categorías para su procesamiento posterior.

    :param layout: Una lista de `LayoutElement` detectados en una página.
    :type layout: List[LayoutElement]
    :return: Una tupla con dos listas: una para regiones de texto y otra para
             regiones de imagen.
    :rtype: Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]
    """
    text_regions = [(element.box, "TextRegion") for element in layout if element.type == "TextRegion"]
    image_regions = [(element, "ImageRegion") for element in layout if element.type == "ImageRegion"]
    return text_regions, image_regions