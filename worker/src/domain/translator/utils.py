import os
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
def clean_text(text: str) -> str:
    """Limpia el texto eliminando caracteres no deseados"""
    text = text.replace("\f", "").replace("\n", " ")
    return text.strip()

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# Registro de fuente Open Sans
pdfmetrics.registerFont(TTFont('OpenSans', os.path.join(FONTS_DIR, 'OpenSans-Regular.ttf')))

# Fuentes CID para idiomas CJK
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))  # Japanese
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))  # Korean
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # Chinese

def get_font_for_language(target_language: str) -> str:
    """Devuelve la fuente apropiada según el idioma destino"""
    cjk_fonts = {
        'jp': 'HeiseiMin-W3',  # Japanese
        'kr': 'HYSMyeongJo-Medium',  # Korean
        'cn': 'STSong-Light',  # Chinese
    }
    
    # Devolver fuente CJK si es necesario
    if target_language in cjk_fonts:
        return cjk_fonts[target_language]
    
    # Usar Open Sans para otros idiomas
    return 'OpenSans'

def adjust_paragraph_font_size(paragraph: Paragraph, available_width: float, available_height: float, style: ParagraphStyle, min_font_size: int = 6, max_font_size: int = 72) -> Paragraph:
    """Ajusta el tamaño de fuente para que se ajuste al espacio disponible"""
    w, h = paragraph.wrap(available_width, available_height)
    # Reducir fuente si no cabe
    while h > available_height and style.fontSize > min_font_size:
        style.fontSize -= 1
        style.leading = style.fontSize * 1.2
        paragraph = Paragraph(paragraph.text, style)
        w, h = paragraph.wrap(available_width, available_height)
    # Aumentar fuente si hay espacio
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
