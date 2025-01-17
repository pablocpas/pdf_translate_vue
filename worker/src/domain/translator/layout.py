import layoutparser as lp
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
import logging
from PIL import Image
from ...infrastructure.config.settings import MODEL_CONFIG_PATH, MODEL_PATH, LABEL_MAP, EXTRA_CONFIG

def get_layout(image: Image.Image):
    """
    Obtiene el layout de una imagen utilizando un modelo preentrenado.

    Args:
        image (Image.Image): Imagen de la cual obtener el layout.

    Returns:
        lp.Layout: Layout detectado.
    """
    try:
        model = lp.Detectron2LayoutModel(
            config_path=MODEL_CONFIG_PATH,
            model_path=MODEL_PATH,
            label_map=LABEL_MAP,
            extra_config=EXTRA_CONFIG
        )
        layout = model.detect(image)
        return layout
    except Exception as e:
        logging.error(f"Error al obtener el layout de la imagen: {e}")
        logging.error(f"Config path: {MODEL_CONFIG_PATH}")
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
