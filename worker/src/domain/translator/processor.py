import logging
import io
from typing import List, Tuple, Callable, Dict, Any
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from PIL import Image

from .layout import get_layout, merge_overlapping_text_regions
from .ocr import extract_text_from_image
from .translator import translate_text
from .utils import adjust_paragraph_font_size, clean_text
from ...infrastructure.config.settings import MARGIN, DEBUG_MODE

logger = logging.getLogger(__name__)

def process_pdf(pdf_path: str, output_pdf_path: str, target_language: str, page_start: int, page_end: int, progress_callback: Callable[[int, int], None] = None) -> Dict[str, Any]:
    """
    Process and translate a PDF file.

    :param pdf_path: Path to the input PDF file
    :param output_pdf_path: Path where the translated PDF will be saved
    :param target_language: The target language for translation
    :param page_start: Starting page number
    :param page_end: Ending page number
    :param progress_callback: Function to call for progress updates
    :return: Dictionary containing the result of the operation
    """
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return {"error": str(e)}

    total_pages = len(pages)
    page_end = min(page_end, total_pages)
    pdf_canvas = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_width, page_height = A4

    styles = getSampleStyleSheet()
    base_style = styles["Normal"]

    try:
        for page_num in range(page_start - 1, page_end):
            process_page(pages[page_num], pdf_canvas, page_width, page_height, base_style, target_language)

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

        pdf_canvas.save()
        logger.info(f"Translated PDF saved as {output_pdf_path}")
        return {"success": True, "output_path": output_pdf_path}
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return {"error": str(e)}

def process_page(page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str) -> None:
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
    layout = get_layout(page_image)
    text_regions, image_regions = merge_overlapping_text_regions(layout)

    process_text_regions(text_regions, page_image, pdf_canvas, page_width, page_height, base_style, target_language)
    process_image_regions(image_regions, page_image, pdf_canvas, page_width, page_height)

    pdf_canvas.showPage()

def process_text_regions(text_regions: List[Tuple[Any, Any]], page_image: Image.Image, pdf_canvas: canvas.Canvas, page_width: float, page_height: float, base_style: ParagraphStyle, target_language: str) -> None:
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
            translated_text = translate_text(clean_txt, target_language)

            min_font_size = 8  # Tamaño de fuente mínimo
            font_scale_factor = 0.8  # Ajusta este factor según sea necesario
            initial_font_size = max(min_font_size, frame_height * font_scale_factor)
            paragraph_style = ParagraphStyle(
                name="CustomStyle",
                parent=base_style,
                fontSize=initial_font_size,
                leading=initial_font_size * 1.2  # Ajustar el interlineado
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
