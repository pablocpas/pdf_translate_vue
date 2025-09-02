# src/domain/layout.py

import logging
from typing import List, Tuple, Any, NamedTuple
from PIL import Image
import os

# Dependencias de terceros
from doclayout_yolo import YOLOv10

logger = logging.getLogger(__name__)

# --- Reemplazo de las estructuras de datos de layoutparser (sin cambios) ---

class Rectangle(NamedTuple):
    """
    Un reemplazo simple para lp.Rectangle. Almacena las coordenadas de un cuadro delimitador.
    """
    x_1: float
    y_1: float
    x_2: float
    y_2: float

class LayoutElement(NamedTuple):
    """
    Un reemplazo para los elementos dentro de un lp.Layout. 
    Contiene el cuadro delimitador, el tipo de elemento y la puntuación de confianza.
    """
    box: Rectangle
    type: str
    score: float

# --- Configuración del nuevo modelo YOLOv10 (sin cambios) ---

YOLO_LABEL_MAP = {
    'plain text': 'TextRegion',     # Párrafos de texto
    'title': 'TextRegion',          # Títulos
    'list': 'TextRegion',           # Listas
    'table': 'ImageRegion',         # Tratamos las tablas como imagen para no hacer OCR
    'figure': 'ImageRegion',        # Figuras o imágenes
    'section-header': 'TextRegion', # Encabezados de sección
    'figure_caption': 'TextRegion', # Leyendas de figuras
    'table_caption': 'TextRegion',
    'table_footnote': 'TextRegion',  # Leyendas de tablas
    'isolate_formula': 'ImageRegion',# Fórmulas aisladas como imagen
    'formula_caption': 'TextRegion', # Pie de fórmulas como texto
    'abandon': 'ImageRegion',        # Elementos a ignorar
}

YOLO_MODEL_CONFIG = {
    "yolov10_doc": {
        "local_path": "/app/models/doclayout_yolo_docstructbench_imgsz1024.pt"
    }
}

# --- LÓGICA DE PRECARGA DEL MODELO ---
LAYOUT_MODEL: YOLOv10 = None

# 2. La clase `LayoutModel` (ligeramente adaptada para ser llamada una sola vez)
class LayoutModel:

    def __init__(self, model_type="yolov10_doc"):
        """Inicializa el modelo YOLOv10 usando el archivo local pre-descargado."""
        try:
            config = YOLO_MODEL_CONFIG.get(model_type)
            if not config:
                 logger.warning(f"Modelo {model_type} no encontrado, usando yolov10_doc")
                 config = YOLO_MODEL_CONFIG["yolov10_doc"]
            
            local_path = config['local_path']
            
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"El modelo no se encuentra en {local_path}. Asegúrate de que la imagen Docker se construyó correctamente.")
            
            logger.info(f"Cargando modelo {model_type} desde archivo local: {local_path}")
            self.model = YOLOv10(local_path)
            self.model_type = model_type
            logger.info(f"Modelo {model_type} cargado correctamente desde archivo local")
            
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}", exc_info=True)
            raise

    def get_model(self):
        """Devuelve la instancia del modelo subyacente (YOLOv10)."""
        return self.model

# 3. La función que Celery llamará para inicializar el modelo
def initialize_layout_model():
    """
    Crea una instancia de LayoutModel y guarda el modelo YOLOv10 en la variable global.
    Esta función será llamada por la señal `worker_process_init` de Celery.
    """
    global LAYOUT_MODEL
    if LAYOUT_MODEL is None:
        logger.info("Inicializando el modelo de layout para este proceso worker...")
        # Instanciamos la clase contenedora
        model_wrapper = LayoutModel()
        # Guardamos la instancia del modelo real en nuestra variable global
        LAYOUT_MODEL = model_wrapper.get_model()
    else:
        logger.info("El modelo de layout ya está inicializado en este proceso.")

# --- FUNCIONES QUE USAN EL MODELO PRECARGADO ---

def get_layout(image: Image.Image, confidence: float = 0.45) -> List[LayoutElement]:
    """
    Obtiene el layout de una imagen usando el modelo YOLOv10 que ha sido PRECARGADO.
    """
    # 4. Verificamos que el modelo está cargado y lo usamos
    if LAYOUT_MODEL is None:
        # Si esto ocurre, es un error de configuración. El worker debería haberlo cargado.
        raise RuntimeError("FATAL: El modelo de layout no fue inicializado por el worker de Celery. Revisa la conexión de la señal 'worker_process_init' en tasks.py.")

    try:
        # Usamos directamente el modelo que ya está en la memoria del worker
        det_results = LAYOUT_MODEL.predict(
            source=image,
            conf=confidence,
            device="cpu"
        )

        layout = []
        if not det_results or len(det_results) == 0:
            return []

        # det_results[0] contiene las detecciones de la primera imagen
        detections = det_results[0]
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
        
        return layout
    except Exception as e:
        logger.error(f"Error al obtener el layout de la imagen con el modelo precargado: {e}", exc_info=True)
        return []


def merge_overlapping_text_regions(layout: List[LayoutElement]) -> Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]:
    """
    [VERSIÓN SIN FUSIÓN]
    Separa las regiones de texto y de imagen del layout detectado.
    """
    text_regions = [
        (element.box, "TextRegion")
        for element in layout
        if element.type == "TextRegion"
    ]

    image_regions = [
        (element, "ImageRegion")
        for element in layout
        if element.type == "ImageRegion"
    ]
    return text_regions, image_regions