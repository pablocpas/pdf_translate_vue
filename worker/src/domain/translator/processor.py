"""Módulo de procesamiento de páginas para extracción de datos.

Este módulo contiene la lógica central para analizar imágenes de páginas de PDF.
Su función principal, `extract_page_data_in_batch`, está optimizada para
procesar múltiples páginas de manera eficiente, realizando la detección de
layout en lote y luego el OCR para cada región de texto identificada.
"""

import logging
import os
import time
from typing import List, Any, Dict

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

from .layout import merge_overlapping_text_regions, get_layouts_in_batch
from .ocr import extract_text_from_image
from .utils import adjust_paragraph_font_size, clean_text, get_font_for_language

logger = logging.getLogger(__name__)

OCR_MARGIN_PERCENT = 0.015  # 1.5% de margen

def extract_page_data_in_batch(page_images: List[Image.Image], confidence: float) -> List[Dict[str, Any]]:
    """Procesa un lote de imágenes de página para extraer texto y layout.

    Esta es una función clave para el rendimiento del worker. Realiza la
    detección de layout para todas las imágenes en una sola pasada y luego
    itera sobre cada página para realizar el OCR en las regiones de texto
    detectadas.

    :param page_images: Una lista de objetos `Image` de PIL, cada una representando una página.
    :type page_images: List[Image.Image]
    :param confidence: El umbral de confianza para el modelo de detección de layout.
    :type confidence: float
    :return: Una lista de diccionarios. Cada diccionario contiene los datos
             extraídos de una página, incluyendo regiones de texto, regiones de
             imagen y dimensiones de la página.
    :rtype: List[Dict[str, Any]]
    """
    if not page_images:
        return []
    
    start_total = time.time()
    
    # 1. Segmentación en lote
    start_layout = time.time()
    layouts = get_layouts_in_batch(page_images, confidence=confidence, batch_size=len(page_images))
    logger.info(f"Segmentación de layout para {len(page_images)} páginas completada en {time.time() - start_layout:.2f}s")
    
    final_results = []

    # 2. Procesamiento por páginas (OCR y ensamblaje)
    start_ocr_total = time.time()
    for i, page_image in enumerate(page_images):
        logger.info(f"Procesando OCR para página {i+1}/{len(page_images)}")
        
        try:
            page_layout = layouts[i]
            dpi = 300
            page_width_pts = (page_image.width / dpi) * 72
            page_height_pts = (page_image.height / dpi) * 72
            
            text_layout_regions, image_layout_regions = merge_overlapping_text_regions(page_layout)

            final_text_regions = []
            
            for region_idx, (rect, _) in enumerate(text_layout_regions):
                x1_px, y1_px, x2_px, y2_px = rect
                box_width, box_height = x2_px - x1_px, y2_px - y1_px
                margin_x, margin_y = box_width * OCR_MARGIN_PERCENT, box_height * OCR_MARGIN_PERCENT
                
                cropped_image = page_image.crop((
                    max(0, x1_px - margin_x), max(0, y1_px - margin_y),
                    min(page_image.width, x2_px + margin_x), min(page_image.height, y2_px + margin_y)
                ))
                
                original_text = clean_text(extract_text_from_image(cropped_image))
                
                if original_text:
                    frame_x_pts = x1_px * (page_width_pts / page_image.width)
                    frame_y_pts = (page_image.height - y2_px) * (page_height_pts / page_image.height)
                    frame_width_pts = (x2_px - x1_px) * (page_width_pts / page_image.width)
                    frame_height_pts = (y2_px - y1_px) * (page_height_pts / page_image.height)
                    
                    final_text_regions.append({
                        "id": region_idx,
                        "original_text": original_text,
                        "position": {"x": frame_x_pts, "y": frame_y_pts, "width": frame_width_pts, "height": frame_height_pts},
                        "coordinates": {"x1": x1_px, "y1": y1_px, "x2": x2_px, "y2": y2_px}
                    })

            final_image_regions = []
            for img_idx, (element, _) in enumerate(image_layout_regions):
                x1_px, y1_px, x2_px, y2_px = element.box
                final_image_regions.append({
                    "id": img_idx,
                    "position": {
                        "x": x1_px * (page_width_pts / page_image.width),
                        "y": (page_image.height - y2_px) * (page_height_pts / page_image.height),
                        "width": (x2_px - x1_px) * (page_width_pts / page_image.width),
                        "height": (y2_px - y1_px) * (page_height_pts / page_image.height)
                    },
                    "coordinates": {"x1": x1_px, "y1": y1_px, "x2": x2_px, "y2": y2_px}
                })

            final_results.append({
                "text_regions": final_text_regions,
                "image_regions": final_image_regions,
                "page_dimensions": {"width": page_width_pts, "height": page_height_pts},
                "error": None
            })

        except Exception as e:
            logger.error(f"Error procesando OCR en página {i}: {e}", exc_info=True)
            final_results.append({
                "text_regions": [], "image_regions": [],
                "page_dimensions": {"width": A4[0], "height": A4[1]},
                "error": str(e)
            })
            
    logger.info(f"OCR total para el lote completado en {time.time() - start_ocr_total:.2f}s")
    logger.info(f"Extracción total de datos del lote de {len(page_images)} páginas terminada en {time.time() - start_total:.2f}s")
    return final_results

def regenerate_pdf(output_pdf_path: str, translation_data: dict, position_data: dict, target_language: str) -> dict:
    """Regenera un PDF usando datos de traducción y posición previamente guardados.

    Esta función es una utilidad que permite reconstruir un documento PDF
    rápidamente después de que las traducciones hayan sido editadas manualmente,
    sin necesidad de volver a ejecutar el costoso proceso de OCR y layout.

    :param output_pdf_path: Ruta del archivo donde se guardará el PDF regenerado.
    :type output_pdf_path: str
    :param translation_data: Diccionario que contiene los textos traducidos por página y región.
    :type translation_data: dict
    :param position_data: Diccionario que contiene las dimensiones de página y las posiciones
                          de cada región de texto e imagen.
    :type position_data: dict
    :param target_language: Código del idioma de destino para la selección de fuentes.
    :type target_language: str
    :return: Un diccionario indicando el resultado de la operación.
    :rtype: dict
    """
    try:
        pdf_canvas = canvas.Canvas(output_pdf_path)
        styles = getSampleStyleSheet()
        base_style = styles["Normal"]
        font_name = get_font_for_language(target_language)
        
        translation_lookup = {
            page["page_number"]: {t["id"]: t for t in page["translations"]}
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
                        parent=base_style, fontName=font_name,
                        fontSize=initial_font_size, leading=initial_font_size * 1.2
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