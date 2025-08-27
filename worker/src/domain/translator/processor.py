import logging
import io
import json
import os
from typing import List, Tuple, Any, Dict

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from .layout import get_layout, merge_overlapping_text_regions
from .ocr import extract_text_from_image
from .translator import translate_text
from .utils import adjust_paragraph_font_size, clean_text
from .pdf_utils import get_page_dimensions_from_image
from ...infrastructure.config.settings import MARGIN, DEBUG_MODE

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE FUENTES (Sin cambios) ---
# Register fonts for different scripts
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# Register Open Sans font
pdfmetrics.registerFont(TTFont('OpenSans', os.path.join(FONTS_DIR, 'OpenSans-Regular.ttf')))

# Register CID fonts for CJK languages
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))  # Japanese
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))  # Korean
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # Chinese


def get_font_for_language(target_language: str) -> str:
    """
    Returns the appropriate font based on the target language.
    """
    cjk_fonts = {
        'jp': 'HeiseiMin-W3',
        'kr': 'HYSMyeongJo-Medium',
        'cn': 'STSong-Light',
    }
    if target_language in cjk_fonts:
        return cjk_fonts[target_language]
    return 'OpenSans'


# --- NOTA DE ARQUITECTURA ---
# Las funciones `process_pdf`, `process_page`, `process_text_regions` y `process_image_regions`
# han sido eliminadas. Su lógica ha sido refactorizada y distribuida en:
# 1. `tasks.py`: Para la orquestación del flujo de trabajo paralelo con Celery.
# 2. `extract_and_translate_page_data` (abajo): Para el procesamiento de una única página
#    que devuelve datos estructurados en lugar de dibujar en un lienzo.
# 3. La tarea `combine_pages_task` en `tasks.py`: Que se encarga de ensamblar el PDF
#    final a partir de los datos estructurados.

# Añade esta constante al principio del archivo processor.py o dentro de la función
OCR_MARGIN_PERCENT = 0.015  # 2% de margen

def extract_and_translate_page_data(image_path: str, target_language: str, language_model: str, confidence: float) -> Dict[str, Any]:
    """
    Procesa una sola imagen de página para extraer, traducir y estructurar
    los datos necesarios para la reconstrucción del PDF, sin dibujar.
    """
    try:
        logger.info(f"Procesando datos para la imagen: {image_path}")
        page_image = Image.open(image_path).convert("RGB")
        
        page_width_pts, page_height_pts = get_page_dimensions_from_image(image_path)
        
        layout = get_layout(page_image, confidence=confidence)
        text_layout_regions, image_layout_regions = merge_overlapping_text_regions(layout)

        texts_to_translate = []
        region_metadata = []
        
        for rect, _ in text_layout_regions:
            x1_px, y1_px, x2_px, y2_px = rect

            # --- NUEVA LÓGICA PARA AÑADIR MARGEN ---
            box_width = x2_px - x1_px
            box_height = y2_px - y1_px
            
            # Calcula el margen en píxeles
            margin_x = box_width * OCR_MARGIN_PERCENT
            margin_y = box_height * OCR_MARGIN_PERCENT
            
            # Expande las coordenadas
            x1_expanded = x1_px - margin_x
            y1_expanded = y1_px - margin_y
            x2_expanded = x2_px + margin_x
            y2_expanded = y2_px + margin_y
            
            # Asegúrate de que las coordenadas no se salgan de los límites de la imagen
            x1_crop = max(0, x1_expanded)
            y1_crop = max(0, y1_expanded)
            x2_crop = min(page_image.width, x2_expanded)
            y2_crop = min(page_image.height, y2_expanded)
            # --- FIN DE LA NUEVA LÓGICA ---

            frame_x_pts = x1_px * (page_width_pts / page_image.width)
            frame_y_pts = (page_image.height - y2_px) * (page_height_pts / page_image.height)
            frame_width_pts = (x2_px - x1_px) * (page_width_pts / page_image.width)
            frame_height_pts = (y2_px - y1_px) * (page_height_pts / page_image.height)

            # Recortar imagen para OCR usando las coordenadas expandidas
            cropped_image = page_image.crop((x1_crop, y1_crop, x2_crop, y2_crop))
            
            text = extract_text_from_image(cropped_image)
            clean_txt = clean_text(text)

            if clean_txt:
                texts_to_translate.append(clean_txt)
                region_metadata.append({
                    "position": {
                        "x": frame_x_pts, "y": frame_y_pts, "width": frame_width_pts, "height": frame_height_pts
                    },
                    "coordinates": {
                        "x1": x1_px, "y1": y1_px, "x2": x2_px, "y2": y2_px
                    }
                })
        
        translated_texts = translate_text(texts_to_translate, target_language, language_model)

        final_text_regions = []
        if len(translated_texts) == len(texts_to_translate):
            for i, translated_text in enumerate(translated_texts):
                final_text_regions.append({
                    "id": i,
                    "original_text": texts_to_translate[i],
                    "translated_text": translated_text,
                    "position": region_metadata[i]["position"],
                    "coordinates": region_metadata[i]["coordinates"]
                })
        else:
            logger.warning("La cantidad de traducciones no coincide con los textos originales. Saltando regiones de texto.")


        final_image_regions = []
        for i, (element, _) in enumerate(image_layout_regions):
            x1_px, y1_px, x2_px, y2_px = element.box
            
            final_image_regions.append({
                "id": i,
                "position": {
                    "x": x1_px * (page_width_pts / page_image.width),
                    "y": (page_image.height - y2_px) * (page_height_pts / page_image.height),
                    "width": (x2_px - x1_px) * (page_width_pts / page_image.width),
                    "height": (y2_px - y1_px) * (page_height_pts / page_image.height)
                },
                "coordinates": {"x1": x1_px, "y1": y1_px, "x2": x2_px, "y2": y2_px}
            })
            
        return {
            "text_regions": final_text_regions,
            "image_regions": final_image_regions,
            "page_dimensions": {"width": page_width_pts, "height": page_height_pts}
        }

    except Exception as e:
        logger.error(f"Error al extraer datos de la página {image_path}: {e}", exc_info=True)
        return {
            "text_regions": [],
            "image_regions": [],
            "page_dimensions": {"width": A4[0], "height": A4[1]},
            "error": str(e)
        }

def regenerate_pdf(output_pdf_path: str, translation_data: dict, position_data: dict, target_language: str) -> dict:
    """
    Regenera un PDF usando datos de traducción y posición previamente guardados.
    Ideal para editar traducciones y volver a generar el documento rápidamente.

    Args:
        output_pdf_path (str): Ruta donde guardar el PDF regenerado.
        translation_data (dict): Diccionario con las traducciones, organizado por páginas.
        position_data (dict): Diccionario con las dimensiones de página y posiciones de regiones.
        target_language (str): Idioma de destino para la selección de fuentes.

    Returns:
        Dict: Diccionario con el resultado de la operación.
    """
    try:
        pdf_canvas = canvas.Canvas(output_pdf_path)
        styles = getSampleStyleSheet()
        base_style = styles["Normal"]
        font_name = get_font_for_language(target_language)
        
        translation_lookup = {
            page["page_number"]: {
                t["id"]: t for t in page["translations"]
            }
            for page in translation_data.get("pages", [])
        }
        
        images_dir = output_pdf_path.replace('.pdf', '_images')
        
        for page_pos_data in position_data["pages"]:
            page_num = page_pos_data["page_number"]
            dims = page_pos_data["dimensions"]
            pdf_canvas.setPageSize((dims["width"], dims["height"]))
            
            pdf_canvas.setFillColorRGB(1, 1, 1)
            pdf_canvas.rect(0, 0, dims["width"], dims["height"], fill=1, stroke=0)
            
            page_images_data = next(
                (p["images"] for p in position_data.get("images", []) if p["page_number"] == page_num), []
            )
            for image_data in page_images_data:
                image_path = os.path.join(images_dir, image_data["path"])
                if os.path.exists(image_path):
                    pos = image_data["position"]
                    pdf_canvas.drawImage(image_path, pos["x"], pos["y"], pos["width"], pos["height"])
            
            for region in page_pos_data.get("regions", []):
                translation = translation_lookup.get(page_num, {}).get(region["id"])
                if translation:
                    pos = region["position"]
                    min_font_size = 8
                    initial_font_size = max(min_font_size, pos["height"] * 0.8)
                    p_style = ParagraphStyle(
                        name=f"RegenStyle_p{page_num}_r{region['id']}",
                        parent=base_style,
                        fontName=font_name,
                        fontSize=initial_font_size,
                        leading=initial_font_size * 1.2
                    )
                    paragraph = Paragraph(translation["translated_text"], p_style)
                    paragraph = adjust_paragraph_font_size(paragraph, pos["width"], pos["height"], p_style, min_font_size)
                    paragraph.wrapOn(pdf_canvas, pos["width"], pos["height"])
                    paragraph.drawOn(pdf_canvas, pos["x"], pos["y"])
            
            pdf_canvas.showPage()
        
        pdf_canvas.save()
        logger.info(f"PDF regenerado guardado en {output_pdf_path}")
        
        return {"success": True, "output_path": output_pdf_path}
        
    except Exception as e:
        logger.error(f"Error regenerando el PDF: {e}", exc_info=True)
        return {"error": str(e)}