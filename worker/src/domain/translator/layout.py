import logging
from typing import List, Tuple, Any, NamedTuple
from PIL import Image
import os

# Imports optimizados para evitar carga repetida
try:
    # Intentar importar desde cache de preload
    from preload_models import get_cached_model
    _USE_PRELOAD_CACHE = True
except ImportError:
    _USE_PRELOAD_CACHE = False

# Lazy imports - solo se cargan cuando se necesitan
_YOLO_MODULE = None
_SHAPELY_MODULES = None

def _get_yolo_module():
    """Lazy import de YOLOv10"""
    global _YOLO_MODULE
    if _YOLO_MODULE is None:
        from doclayout_yolo import YOLOv10
        _YOLO_MODULE = YOLOv10
    return _YOLO_MODULE

def _get_shapely_modules():
    """Lazy import de módulos Shapely"""
    global _SHAPELY_MODULES
    if _SHAPELY_MODULES is None:
        from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
        from shapely.ops import unary_union
        _SHAPELY_MODULES = {
            'box': box,
            'Polygon': Polygon,
            'MultiPolygon': MultiPolygon,
            'GeometryCollection': GeometryCollection,
            'unary_union': unary_union
        }
    return _SHAPELY_MODULES

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
            # Intentar usar modelo precargado primero
            if _USE_PRELOAD_CACHE:
                try:
                    cached_model = get_cached_model("yolo_model")
                    if cached_model and hasattr(cached_model, 'model'):
                        logger.info(f"Usando modelo {model_type} desde cache precargado")
                        self.model = cached_model.model
                        self.model_type = model_type
                        return
                except Exception as e:
                    logger.warning(f"No se pudo usar modelo precargado, cargando desde archivo: {e}")
            
            # Fallback: cargar normalmente
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
            YOLOv10 = _get_yolo_module()
            self.model = YOLOv10(local_path)
            self.model_type = model_type
            logger.info(f"Modelo {model_type} cargado correctamente desde archivo local")
            
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo."""
        return self.model


def get_layout(image: Image.Image, model_type="yolov10_doc", confidence: float = 0.45) -> List[LayoutElement]:
    """
    Obtiene el layout de una imagen usando el modelo YOLOv10 especificado.
    
    Args:
        image: Imagen a procesar (en formato PIL.Image o ruta de archivo).
        model_type: Tipo de modelo a usar (actualmente solo 'yolov10_doc').
    
    Returns:
        Una lista de objetos LayoutElement, que es el análogo al antiguo lp.Layout.
    """
    try:
        model = LayoutModel(model_type).get_model()
        
        # El modelo YOLOv10 espera una ruta de archivo o un array numpy, no un objeto PIL directamente.
        # Si la entrada es un objeto PIL, debemos convertirla.
        # Por simplicidad, el ejemplo de la librería usa rutas, pero se puede adaptar para numpy.
        det_results = model.predict(
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
            
            # Mapear la clase detectada a nuestro tipo estándar ("TextRegion", "ImageRegion")
            region_type = YOLO_LABEL_MAP.get(class_name)
            
            if region_type:
                layout.append(LayoutElement(
                    box=Rectangle(x_1=x1, y_1=y1, x_2=x2, y_2=y2),
                    type=region_type,
                    score=score
                ))
        
        return layout
    except Exception as e:
        logger.error(f"Error al obtener el layout de la imagen: {e}")
        return []


def merge_overlapping_text_regions(layout: List[LayoutElement]) -> Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]:
    """
    [VERSIÓN MODIFICADA - SIN FUSIÓN]
    Separa las regiones de texto y de imagen del layout detectado.
    La fusión con unary_union ha sido desactivada, ya que el modelo YOLOv10
    suele generar bloques de texto coherentes que no necesitan ser fusionados.

    Args:
        layout (List[LayoutElement]): Layout detectado por el modelo.

    Returns:
        Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]:
            Una tupla con:
            1. Regiones de texto originales como (Rectangle, "TextRegion").
            2. Regiones de imagen originales como (LayoutElement, "ImageRegion").
    """
    logger.info("Separando regiones de texto e imagen sin fusionar.")
    
    # Simplemente extraemos las regiones de texto y las devolvemos con el formato esperado.
    # El formato de retorno para texto es List[Tuple[Rectangle, str]]
    text_regions = [
        (element.box, "TextRegion")
        for element in layout
        if element.type == "TextRegion"
    ]

    # El formato para imágenes es List[Tuple[LayoutElement, str]]
    image_regions = [
        (element, "ImageRegion")
        for element in layout
        if element.type == "ImageRegion"
    ]

    return text_regions, image_regions