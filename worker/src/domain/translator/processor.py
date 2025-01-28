import logging
import io
import json
from typing import List, Tuple, Callable, Dict, Any
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from PIL import Image
import os

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
        'jp': 'HeiseiMin-W3',  # Japanese
        'kr': 'HYSMyeongJo-Medium',  # Korean
        'cn': 'STSong-Light',  # Chinese
    }
    
    # Return CJK font if language is CJK
    if target_language in cjk_fonts:
        return cjk_fonts[target_language]
    
    # Use Open Sans for all other scripts (Latin, Cyrillic, Greek, etc.)
    return 'OpenSans'

from .layout import get_layout, merge_overlapping_text_regions
from .ocr import extract_text_from_image
from .translator import translate_text
from .utils import adjust_paragraph_font_size, clean_text
from ...infrastructure.config.settings import MARGIN, DEBUG_MODE

logger = logging.getLogger(__name__)

def process_pdf(pdf_path, output_pdf_path, target_language, progress_callback=None, model_type="primalayout"):
    # Store translation data for all pages
    all_translation_data = []
    try:
        # Escoge un DPI adecuado (por ejemplo, 300)
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return {"error": str(e)}

    total_pages = len(pages)
    
    # NOTA: Creamos el canvas SIN tamaño fijo:
    pdf_canvas = canvas.Canvas(output_pdf_path)
    styles = getSampleStyleSheet()
    base_style = styles["Normal"]

    try:
        for page_num, page_image in enumerate(pages):
            # Calculamos tamaño en puntos a partir de los píxeles y el DPI
            width_px, height_px = page_image.size
            dpi = 300  # El mismo que usaste en convert_from_path
            page_width_pts = (width_px * 72.0) / dpi
            page_height_pts = (height_px * 72.0) / dpi

            # Establecemos el tamaño de página actual
            pdf_canvas.setPageSize((page_width_pts, page_height_pts))

            # Llamamos a la función que dibuja texto e imágenes y guardamos los datos de traducción
            page_translation_data = process_page(
                page_image,
                pdf_canvas,
                page_width_pts,
                page_height_pts,
                base_style,
                target_language,
                model_type
            )
            all_translation_data.append(page_translation_data)

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            # Finalizamos la página
            pdf_canvas.showPage()

        # Cerramos el documento final
        pdf_canvas.save()
        logger.info(f"Translated PDF saved as {output_pdf_path}")
        # Save translation data to JSON files
        translation_data_path = output_pdf_path.replace('.pdf', '_translation_data.json')
        position_data_path = output_pdf_path.replace('.pdf', '_translation_data_position.json')
        images_data_path = output_pdf_path.replace('.pdf', '_images')
        os.makedirs(images_data_path, exist_ok=True)

        logger.info(f"Saving translation data to: {translation_data_path}")
        logger.info(f"Translation data content: {json.dumps(all_translation_data, indent=2)}")
        
        # Organize translations by page
        translations_by_page = []
        for page_idx, page_data in enumerate(all_translation_data):
            translations_by_page.append({
                "page_number": page_idx,
                "translations": [
                    {
                        "id": r["id"],
                        "original_text": r["original_text"],
                        "translated_text": r["translated_text"]
                    }
                    for r in page_data["text_regions"]
                ]
            })
            
        # Save translations with page structure
        with open(translation_data_path, 'w') as f:
            json.dump({"pages": translations_by_page}, f, ensure_ascii=False, indent=2)

        # Save positions and image regions
        page_image_data = []
        for idx, page in enumerate(all_translation_data):
            # Extract image regions
            layout = get_layout(pages[idx], model_type)
            _, image_regions = merge_overlapping_text_regions(layout)
            
            # Save each image region
            page_images = []
            for i, (element, _) in enumerate(image_regions):
                x1, y1, x2, y2 = element.coordinates
                cropped_image = pages[idx].crop((
                    max(x1 - MARGIN, 0),
                    max(y1 - MARGIN, 0),
                    min(x2 + MARGIN, pages[idx].width),
                    min(y2 + MARGIN, pages[idx].height)
                ))
                
                # Save image
                image_filename = f"page_{idx}_image_{i}.png"
                image_path = os.path.join(images_data_path, image_filename)
                cropped_image.save(image_path)
                
                # Store image data
                page_images.append({
                    "path": image_filename,
                    "position": {
                        "x": x1 * (page["page_dimensions"]["width"] / pages[idx].width),
                        "y": (pages[idx].height - y2) * (page["page_dimensions"]["height"] / pages[idx].height),
                        "width": (x2 - x1) * (page["page_dimensions"]["width"] / pages[idx].width),
                        "height": (y2 - y1) * (page["page_dimensions"]["height"] / pages[idx].height)
                    }
                })
            
            page_image_data.append({
                "page_number": idx,
                "images": page_images
            })

        # Save positions and image data
        with open(position_data_path, 'w') as f:
            json.dump({
                "pages": [
                    {
                        "page_number": idx,
                        "dimensions": page["page_dimensions"],
                        "regions": [
                            {
                                "id": r["id"],
                                "position": r["position"],
                                "coordinates": r["position"]["coordinates"]
                            }
                            for r in page["text_regions"]
                        ]
                    }
                    for idx, page in enumerate(all_translation_data)
                ],
                "images": page_image_data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info("Translation data saved successfully")
        result = {
            "success": True, 
            "output_path": output_pdf_path,
            "translation_data_path": translation_data_path
        }
        logger.info(f"Returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return {"error": str(e)}

def process_page(page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str, model_type: str) -> dict:
    """
    Process a single page of the PDF.

    :param page_image: PIL Image of the page
    :param pdf_canvas: ReportLab canvas to draw on
    :param page_width: Width of the page
    :param page_height: Height of the page
    :param base_style: Base style for paragraphs
    :param target_language: The target language for translation
    """
    page_image = page_image.convert("RGB")
    layout = get_layout(page_image, model_type)
    text_regions, image_regions = merge_overlapping_text_regions(layout)

    translation_data = process_text_regions(text_regions, page_image, pdf_canvas, page_width, page_height, base_style, target_language)
    process_image_regions(image_regions, page_image, pdf_canvas, page_width, page_height)
    
    return {
        "text_regions": translation_data,
        "page_dimensions": {
            "width": page_width,
            "height": page_height
        }
    }
    

def process_text_regions(text_regions: List[Tuple[Any, Any]], page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str) -> List[dict]:
    # Set the appropriate font for the target language
    font_name = get_font_for_language(target_language)
    """
    Process text regions of a page.

    :param text_regions: List of text regions to process
    :param page_image: PIL Image of the page
    :param pdf_canvas: ReportLab canvas to draw on
    :param page_width: Width of the page
    :param page_height: Height of the page
    :param base_style: Base style for paragraphs
    :param target_language: The target language for translation
    """
    texts_to_translate = []
    regions_data = []
    
    for rect, _ in text_regions:
        x1, y1, x2, y2 = rect.coordinates

        frame_x = x1 * (page_width / page_image.width)
        frame_y = (page_image.height - y2) * (page_height / page_image.height)
        frame_width = (x2 - x1) * (page_width / page_image.width)
        frame_height = (y2 - y1) * (page_height / page_image.height)

        cropped_image = page_image.crop((
            max(x1 - MARGIN, 0),
            max(y1 - MARGIN, 0),
            min(x2 + MARGIN, page_image.width),
            min(y2 + MARGIN, page_image.height)
        ))

        text = extract_text_from_image(cropped_image)
        clean_txt = clean_text(text)

        if clean_txt:
            texts_to_translate.append(clean_txt)
            regions_data.append((frame_x, frame_y, frame_width, frame_height, rect))

    # Traducción por página usando structured output
    print("Traduciendo texto...")
    print(texts_to_translate)
    print(target_language)
    translated_texts = translate_text(texts_to_translate, target_language)

    # Preparar datos de traducción
    translation_data = []
    
    # Procesar textos traducidos
    for i, (translated_text, (frame_x, frame_y, frame_width, frame_height, rect)) in enumerate(zip(translated_texts, regions_data)):
        # Guardar datos de traducción
        translation_data.append({
            "id": i,
            "original_text": texts_to_translate[i],
            "translated_text": translated_text,
            "position": {
                "x": frame_x,
                "y": frame_y,
                "width": frame_width,
                "height": frame_height,
                "coordinates": {
                    "x1": rect.coordinates[0],
                    "y1": rect.coordinates[1],
                    "x2": rect.coordinates[2],
                    "y2": rect.coordinates[3]
                }
            }
        })
        min_font_size = 8
        font_scale_factor = 0.8
        initial_font_size = max(min_font_size, frame_height * font_scale_factor)
        paragraph_style = ParagraphStyle(
            name="CustomStyle",
            parent=base_style,
            fontName=font_name,
            fontSize=initial_font_size,
            leading=initial_font_size * 1.2,
            encoding='utf-8'
        )
        paragraph = Paragraph(translated_text, paragraph_style)
        paragraph = adjust_paragraph_font_size(
            paragraph, frame_width, frame_height, paragraph_style, min_font_size
        )
        paragraph.wrapOn(pdf_canvas, frame_width, frame_height)
        paragraph.drawOn(pdf_canvas, frame_x, frame_y)
        
    return translation_data

def regenerate_pdf(output_pdf_path: str, translation_data: dict, position_data: dict, target_language: str) -> dict:
    """
    Regenerate PDF using existing translation and position data.
    
    :param output_pdf_path: Path where to save the regenerated PDF
    :param translation_data: List of translation entries
    :param position_data: Dictionary containing page positions and image data
    :param target_language: Target language for font selection
    :return: Dictionary with result information
    """
    try:
        # Create PDF canvas
        pdf_canvas = canvas.Canvas(output_pdf_path)
        styles = getSampleStyleSheet()
        base_style = styles["Normal"]
        font_name = get_font_for_language(target_language)
        
        # Create translation lookup by page number and id
        translation_lookup = {}
        if isinstance(translation_data, dict) and "pages" in translation_data:
            logger.info("Processing translation data in page-based format")
            for page in translation_data["pages"]:
                page_num = page["page_number"]
                if page_num not in translation_lookup:
                    translation_lookup[page_num] = {}
                for translation in page["translations"]:
                    translation_lookup[page_num][translation["id"]] = translation
                logger.info(f"Added {len(page['translations'])} translations for page {page_num}")
        else:
            # Handle legacy format (flat list) - put all in page 0
            logger.info("Processing translation data in legacy format")
            translation_lookup[0] = {}
            for translation in translation_data:
                translation_lookup[0][translation["id"]] = translation
            logger.info(f"Added {len(translation_data)} translations to page 0")
        
        # Get images directory path
        images_dir = output_pdf_path.replace('.pdf', '_images')
        
        # Process each page
        for page_data in position_data["pages"]:
            # Set page size
            dimensions = page_data["dimensions"]
            pdf_canvas.setPageSize((dimensions["width"], dimensions["height"]))
            
            # Create white background
            pdf_canvas.setFillColorRGB(1, 1, 1)  # White
            pdf_canvas.rect(0, 0, dimensions["width"], dimensions["height"], fill=1)
            
            # Draw saved images
            page_images = next(
                (p["images"] for p in position_data["images"] if p["page_number"] == page_data["page_number"]),
                []
            )
            for image_data in page_images:
                image_path = os.path.join(images_dir, image_data["path"])
                if os.path.exists(image_path):
                    pos = image_data["position"]
                    pdf_canvas.drawImage(
                        image_path,
                        pos["x"],
                        pos["y"],
                        pos["width"],
                        pos["height"]
                    )
            
            # Draw text regions
            for region in page_data["regions"]:
                current_page = page_data["page_number"]
                page_translations = translation_lookup.get(current_page, {})
                translation = page_translations.get(region["id"])
                if translation:
                    logger.info(f"Found translation for page {current_page}, region {region['id']}")
                    pos = region["position"]
                    
                    # Create paragraph style
                    min_font_size = 8
                    font_scale_factor = 0.8
                    initial_font_size = max(min_font_size, pos["height"] * font_scale_factor)
                    paragraph_style = ParagraphStyle(
                        name=f"CustomStyle_{region['id']}",
                        parent=base_style,
                        fontName=font_name,
                        fontSize=initial_font_size,
                        leading=initial_font_size * 1.2,
                        encoding='utf-8'
                    )
                    
                    # Create and adjust paragraph
                    paragraph = Paragraph(translation["translated_text"], paragraph_style)
                    paragraph = adjust_paragraph_font_size(
                        paragraph, pos["width"], pos["height"], paragraph_style, min_font_size
                    )
                    
                    # Draw paragraph
                    paragraph.wrapOn(pdf_canvas, pos["width"], pos["height"])
                    paragraph.drawOn(pdf_canvas, pos["x"], pos["y"])
            
            pdf_canvas.showPage()
        
        pdf_canvas.save()
        logger.info(f"Regenerated PDF saved as {output_pdf_path}")
        
        return {
            "success": True,
            "output_path": output_pdf_path
        }
        
    except Exception as e:
        logger.error(f"Error regenerating PDF: {e}")
        return {"error": str(e)}

def process_image_regions(image_regions: List[Tuple[Any, Any]], page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float) -> None:
    """
    Process image regions of a page.

    :param image_regions: List of image regions to process
    :param page_image: PIL Image of the page
    :param pdf_canvas: ReportLab canvas to draw on
    :param page_width: Width of the page
    :param page_height: Height of the page
    """
    for element, _ in image_regions:
        x1, y1, x2, y2 = element.coordinates

        frame_x = x1 * (page_width / page_image.width)
        frame_y = (page_image.height - y2) * (page_height / page_image.height)
        frame_width = (x2 - x1) * (page_width / page_image.width)
        frame_height = (y2 - y1) * (page_height / page_image.height)

        if DEBUG_MODE:
            pdf_canvas.setStrokeColorRGB(0, 0, 1)
            pdf_canvas.rect(frame_x, frame_y, frame_width, frame_height, stroke=1, fill=0)

        cropped_image = page_image.crop((
            max(x1 - MARGIN, 0),
            max(y1 - MARGIN, 0),
            min(x2 + MARGIN, page_image.width),
            min(y2 + MARGIN, page_image.height)
        ))

        img_byte_arr = io.BytesIO()
        cropped_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        pdf_image = ImageReader(img_byte_arr)
        pdf_canvas.drawImage(pdf_image, frame_x, frame_y, frame_width, frame_height)
