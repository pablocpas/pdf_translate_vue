import logging
import os
from typing import List, Tuple, NamedTuple
from PIL import Image

from doclayout_yolo import YOLOv10

logger = logging.getLogger(__name__)

# --- Reemplazo de las estructuras de datos de layoutparser ---

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

# --- Configuración del nuevo modelo YOLOv10 ---

# Mapeo de las clases del modelo YOLO a los tipos que usábamos ("TextRegion", "ImageRegion")
# DocLayout-YOLO detecta más clases, las agrupamos según su naturaleza.
YOLO_LABEL_MAP = {
    'plain text': 'TextRegion',     # Párrafos de texto
    'title': 'TextRegion',          # Títulos
    'list': 'TextRegion',           # Listas
    'table': 'ImageRegion',          # Tratamos las tablas como texto para OCR/traducción
    'figure': 'ImageRegion',        # Figuras o imágenes
    #'header': 'TextRegion',         # Encabezados de página
    #'footer': 'TextRegion',         # Pies de página
    'section-header': 'TextRegion', # Encabezados de sección
    'figure_caption': 'TextRegion', # Leyendas de figuras
    'table_caption': 'TextRegion',
    'table_footnote': 'TextRegion',  # Leyendas de tablas
    'isolate_formula': 'ImageRegion',
    'formula_caption': 'TextRegion',       # Fórmulas (pueden ser tratadas como imagen si el OCR falla)
    'abandon': 'ImageRegion',
}

# Configuración del modelo YOLOv10 local (pre-descargado en la imagen Docker)
YOLO_MODEL_CONFIG = {
    "yolov10_doc": {
        "local_path": "/app/models/doclayout_yolo_docstructbench_imgsz1024.pt"
    }
}

class LayoutModel:
    _instances = {}  # Diccionario para almacenar instancias por tipo de modelo

    def __new__(cls, model_type="yolov10_doc"):
        """Garantiza que solo se cree una instancia por tipo de modelo."""
        if model_type not in cls._instances:
            instance = super(LayoutModel, cls).__new__(cls)
            instance._initialize_model(model_type)
            cls._instances[model_type] = instance
        return cls._instances[model_type]

    def _initialize_model(self, model_type):
        """Inicializa el modelo YOLOv10 usando el archivo local pre-descargado."""
        try:
            if model_type not in YOLO_MODEL_CONFIG:
                logger.warning(f"Modelo {model_type} no encontrado, usando yolov10_doc")
                model_type = "yolov10_doc"

            config = YOLO_MODEL_CONFIG[model_type]
            local_path = config['local_path']
            
            # Verificar que el archivo local existe
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"El modelo no se encuentra en {local_path}. "
                                      "Asegúrate de que la imagen Docker se construyó correctamente.")
            
            logger.info(f"Cargando modelo {model_type} desde archivo local: {local_path}")
            self.model = YOLOv10(local_path)
            self.model_type = model_type
            logger.info(f"Modelo {model_type} cargado correctamente desde archivo local")
            
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo."""
        return self.model


# --- NUEVA FUNCIÓN DE BATCHING ---
def get_layouts_in_batch(images: List[Image.Image], model_type="yolov10_doc", confidence: float = 0.45, batch_size: int = 16) -> List[List[LayoutElement]]:
    """
    Obtiene el layout para una lista de imágenes usando inferencia por lotes.
    
    Args:
        images: Lista de imágenes a procesar (objetos PIL.Image).
        model_type: Tipo de modelo a usar.
        confidence: Umbral de confianza para las detecciones.
        batch_size: Tamaño del lote para la inferencia del modelo.
    
    Returns:
        Una lista de layouts. Cada layout es una lista de objetos LayoutElement.
    """
    if not images:
        return []

    try:
        model = LayoutModel(model_type).get_model()
        
        # Realizar la predicción en lote. El modelo YOLOv10 acepta una lista de imágenes.
        # El parámetro 'batch' se pasa directamente al predictor.
        det_results_batch = model.predict(
            source=images,
            conf=confidence,
            device="cpu",
            batch=batch_size # Parámetro clave para la inferencia en lote
        )

        all_layouts = []
        if not det_results_batch:
            return [[] for _ in images]

        # det_results_batch es una lista, cada elemento corresponde a una imagen de entrada
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
        # Devolver una lista de layouts vacíos con la misma longitud que la entrada
        return [[] for _ in images]


def merge_overlapping_text_regions(layout: List[LayoutElement]) -> Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]:
    """
    (Sin cambios) Separa las regiones de texto y de imagen.
    """
    text_regions = [
        (element.box, "TextRegion")
        for element in layout if element.type == "TextRegion"
    ]
    image_regions = [
        (element, "ImageRegion")
        for element in layout if element.type == "ImageRegion"
    ]
    return text_regions, image_regions