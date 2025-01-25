import layoutparser as lp
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
import logging
from PIL import Image
from ...infrastructure.config.settings import MODEL_CONFIGS, LABEL_MAPS, EXTRA_CONFIG

logger = logging.getLogger(__name__)

class LayoutModel:
    _instances = {}  # Dictionary to store instances for each model type

    def __new__(cls, model_type="primalayout"):
        """Garantiza que solo se cree una instancia por tipo de modelo."""
        if model_type not in cls._instances:
            instance = super(LayoutModel, cls).__new__(cls)
            instance._initialize_model(model_type)
            cls._instances[model_type] = instance
        return cls._instances[model_type]

    def _initialize_model(self, model_type):
        """Inicializa el modelo Detectron2LayoutModel con la configuración específica."""
        try:
            if model_type not in MODEL_CONFIGS:
                logger.warning(f"Modelo {model_type} no encontrado, usando primalayout")
                model_type = "primalayout"

            config = MODEL_CONFIGS[model_type]
            self.model = lp.Detectron2LayoutModel(
                config_path=config['config_path'],
                model_path=config['model_path'],
                label_map=LABEL_MAPS[model_type],
                extra_config=EXTRA_CONFIG
            )
            logger.info(f"Modelo {model_type} cargado correctamente")
        except Exception as e:
            logger.error(f"Error cargando el modelo {model_type}: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo."""
        return self.model


def get_layout(image, model_type="primalayout"):
    """
    Obtiene el layout de una imagen usando el modelo especificado.
    
    Args:
        image: Imagen a procesar
        model_type: Tipo de modelo a usar ('primalayout' o 'publaynet')
    
    Returns:
        Layout detectado
    """
    try:
        model = LayoutModel(model_type).get_model()
        layout = model.detect(image)
        return layout
    except Exception as e:
        logger.error(f"Error al obtener el layout de la imagen: {e}")
        return lp.Layout([])


def merge_overlapping_text_regions(layout: lp.Layout):
    """
    Fusiona regiones de texto superpuestas y separa las regiones de imagen.

    Args:
        layout (lp.Layout): Layout detectado por el modelo.

    Returns:
        Tuple[List[Tuple[lp.Rectangle, str]], List[Tuple[Any, str]]]: 
            Regiones de texto fusionadas y regiones de imagen.
    """
    # Extraer regiones de texto e imagen
    text_rects = [
        box(*element.coordinates)
        for element in layout
        if element.type == "TextRegion"
    ]
    images = [element for element in layout if element.type == "ImageRegion"]

    # Fusionar regiones de texto superpuestas
    merged_text_polygons = unary_union(text_rects)
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
        new_text_regions.append((lp.Rectangle(minx, miny, maxx, maxy), "TextRegion"))

    # Retornar regiones de texto fusionadas y imágenes
    return new_text_regions, [(img, "ImageRegion") for img in images]
