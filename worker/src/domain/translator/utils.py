from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import logging

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
