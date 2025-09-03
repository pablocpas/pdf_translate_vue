from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import logging
import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
def clean_text(text: str) -> str:
    """
    Limpia el texto eliminando caracteres no deseados.

    Args:
        text (str): Texto a limpiar.

    Returns:
        str: Texto limpio.
    """
    text = text.replace("\f", "").replace("\n", " ")
    return text.strip()

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
    

def adjust_paragraph_font_size(paragraph: Paragraph, available_width: float, available_height: float, style: ParagraphStyle, min_font_size: int = 6, max_font_size: int = 72) -> Paragraph:
    """
    Ajusta el tamaño de fuente de un párrafo para que se ajuste al espacio disponible.

    Args:
        paragraph (Paragraph): Párrafo a ajustar.
        available_width (float): Ancho disponible.
        available_height (float): Alto disponible.
        style (ParagraphStyle): Estilo del párrafo.
        min_font_size (int): Tamaño mínimo de fuente.

    Returns:
        Paragraph: Párrafo ajustado.
    """
    w, h = paragraph.wrap(available_width, available_height)
    # Reducir tamaño de fuente si el texto no cabe
    while h > available_height and style.fontSize > min_font_size:
        style.fontSize -= 1
        style.leading = style.fontSize * 1.2
        paragraph = Paragraph(paragraph.text, style)
        w, h = paragraph.wrap(available_width, available_height)
    # Aumentar tamaño de fuente si hay espacio extra
    while h < available_height and style.fontSize < max_font_size:
        style.fontSize += 1
        style.leading = style.fontSize * 1.2
        paragraph = Paragraph(paragraph.text, style)
        w, h = paragraph.wrap(available_width, available_height)
        if h > available_height:
            style.fontSize -= 1
            style.leading = style.fontSize * 1.2
            paragraph = Paragraph(paragraph.text, style)
            break
    return paragraph
