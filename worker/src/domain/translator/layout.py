import layoutparser as lp
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
import logging
from PIL import Image
from ...infrastructure.config.settings import MODEL_CONFIG_PATH, MODEL_PATH, LABEL_MAP, EXTRA_CONFIG
# Variable global para el modelo

class LayoutModel:
    _instance = None  # Variable estática para almacenar la instancia única del modelo

    def __new__(cls, *args, **kwargs):
        """Garantiza que solo se cree una instancia del modelo."""
        if cls._instance is None:
            cls._instance = super(LayoutModel, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        """Inicializa el modelo Detectron2LayoutModel."""
        try:
            self.model = lp.Detectron2LayoutModel(
                config_path=MODEL_CONFIG_PATH,
                model_path=MODEL_PATH,
                label_map=LABEL_MAP,
                extra_config=EXTRA_CONFIG
            )
            logging.info("Modelo Detectron2LayoutModel cargado correctamente.")
        except Exception as e:
            logging.error(f"Error cargando el modelo Detectron2LayoutModel: {e}")
            raise

    def get_model(self):
        """Devuelve la instancia del modelo."""
        return self.model


def get_layout(image):
    try:
        model = LayoutModel().get_model()
        layout = model.detect(image)
        return layout
    except Exception as e:
        logging.error(f"Error al obtener el layout de la imagen: {e}")
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
