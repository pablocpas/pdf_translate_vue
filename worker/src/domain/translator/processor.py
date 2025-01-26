import logging
import io
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
        'ja': 'HeiseiMin-W3',  # Japanese
        'ko': 'HYSMyeongJo-Medium',  # Korean
        'zh': 'STSong-Light',  # Chinese
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

            # Llamamos a la función que dibuja texto e imágenes
            process_page(
                page_image,
                pdf_canvas,
                page_width_pts,
                page_height_pts,
                base_style,
                target_language,
                model_type
            )

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            # Finalizamos la página
            pdf_canvas.showPage()

        # Cerramos el documento final
        pdf_canvas.save()
        logger.info(f"Translated PDF saved as {output_pdf_path}")
        return {"success": True, "output_path": output_pdf_path}
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return {"error": str(e)}

def process_page(page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str, model_type: str) -> None:
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

    process_text_regions(text_regions, page_image, pdf_canvas, page_width, page_height, base_style, target_language)
    process_image_regions(image_regions, page_image, pdf_canvas, page_width, page_height)
    

def process_text_regions(text_regions: List[Tuple[Any, Any]], page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str) -> None:
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

    # Procesar textos traducidos
    for translated_text, (frame_x, frame_y, frame_width, frame_height, _) in zip(translated_texts, regions_data):
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
