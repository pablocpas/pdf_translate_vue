import logging
from typing import List, Tuple, Any, NamedTuple
from PIL import Image

# Nuevas dependencias
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

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
    'text': 'TextRegion',
    'title': 'TextRegion',
    'list': 'TextRegion',
    'table': 'ImageRegion', # Podrías manejar tablas de forma diferente si quisieras
    'figure': 'ImageRegion',
    'page-header': 'TextRegion',
    'page-footer': 'TextRegion',
    'section-header': 'TextRegion',
    'equation': 'TextRegion',
    'toc': 'TextRegion'
}

# Configuración del modelo YOLOv10 a cargar desde Hugging Face Hub
YOLO_MODEL_CONFIG = {
    "yolov10_doc": {
        "repo_id": "juliozhao/DocLayout-YOLO-DocStructBench",
        "filename": "doclayout_yolo_docstructbench_imgsz1024.pt"
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
        """Inicializa el modelo YOLOv10 con la configuración específica."""
        try:
            if model_type not in YOLO_MODEL_CONFIG:
                logger.warning(f"Modelo {model_type} no encontrado, usando yolov10_doc")
                model_type = "yolov10_doc"

            config = YOLO_MODEL_CONFIG[model_type]
            
            logger.info(f"Descargando el modelo {model_type} desde Hugging Face Hub...")
            filepath = hf_hub_download(
                repo_id=config['repo_id'],
                filename=config['filename']
            )
            
            logger.info("Inicializando el modelo YOLOv10...")
            self.model = YOLOv10(filepath)
            self.model_type = model_type
            logger.info(f"Modelo {model_type} cargado correctamente")
            
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo."""
        return self.model


def get_layout(image: Image.Image, model_type="yolov10_doc") -> List[LayoutElement]:
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
            conf=0.25,
            device="cpu"  # Cambiar a "cuda:0" si tienes una GPU disponible
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
    Fusiona regiones de texto superpuestas y separa las regiones de imagen.

    Args:
        layout (List[LayoutElement]): Layout detectado por el modelo.

    Returns:
        Tuple[List[Tuple[Rectangle, str]], List[Tuple[LayoutElement, str]]]: 
            Una tupla con:
            1. Regiones de texto fusionadas como (Rectangle, "TextRegion").
            2. Regiones de imagen originales como (LayoutElement, "ImageRegion").
    """
    # Extraer regiones de texto e imagen
    text_boxes = [
        box(*element.box)
        for element in layout
        if element.type == "TextRegion"
    ]
    images = [element for element in layout if element.type == "ImageRegion"]

    if not text_boxes:
        return [], [(img, "ImageRegion") for img in images]

    # Fusionar regiones de texto superpuestas
    merged_text_polygons = unary_union(text_boxes)
    new_text_regions = []

    def extract_polygons(geometry):
        """
        Extrae polígonos individuales de una geometría, manejando Polygon, MultiPolygon y GeometryCollection.
        """
        if isinstance(geometry, Polygon):
            return [geometry]
        elif isinstance(geometry, MultiPolygon):
            return list(geometry.geoms)
        elif isinstance(geometry, GeometryCollection):
            polygons = []
            for geom in geometry.geoms:
                polygons.extend(extract_polygons(geom))
            return polygons
        else:
            return []

    polygons = extract_polygons(merged_text_polygons)

    for polygon in polygons:
        minx, miny, maxx, maxy = polygon.bounds
        new_text_regions.append((Rectangle(minx, miny, maxx, maxy), "TextRegion"))

    # Retornar regiones de texto fusionadas y imágenes
    return new_text_regions, [(img, "ImageRegion") for img in images]