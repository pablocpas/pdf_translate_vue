"""Módulo de utilidades generales para el procesamiento de documentos.

Contiene funciones auxiliares para tareas comunes como la limpieza de texto,
la gestión de fuentes para la generación de PDFs y el ajuste dinámico del
tamaño de fuente para que el texto encaje en un cuadro delimitador.
"""
import os
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

def clean_text(text: str) -> str:
    """Limpia una cadena de texto eliminando saltos de página y de línea.

    :param text: El texto a limpiar.
    :type text: str
    :return: El texto limpio y sin espacios extra al principio o al final.
    :rtype: str
    """
    text = text.replace("\f", "").replace("\n", " ")
    return text.strip()

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# Registro de fuentes para ReportLab
pdfmetrics.registerFont(TTFont('OpenSans', os.path.join(FONTS_DIR, 'OpenSans-Regular.ttf')))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))  # Japanese
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))  # Korean
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # Chinese

def get_font_for_language(target_language: str) -> str:
    """Selecciona y devuelve el nombre de la fuente apropiada para un idioma.

    Utiliza fuentes CID especiales para idiomas CJK (Chino, Japonés, Coreano)
    para garantizar la correcta renderización de los caracteres. Para el resto
    de idiomas, utiliza 'OpenSans'.

    :param target_language: El código ISO del idioma de destino.
    :type target_language: str
    :return: El nombre de la fuente registrada en ReportLab.
    :rtype: str
    """
    cjk_fonts = {
        'jp': 'HeiseiMin-W3',
        'kr': 'HYSMyeongJo-Medium',
        'cn': 'STSong-Light',
    }
    return cjk_fonts.get(target_language, 'OpenSans')

def adjust_paragraph_font_size(paragraph: Paragraph, available_width: float, available_height: float, style: ParagraphStyle, min_font_size: int = 6, max_font_size: int = 72) -> Paragraph:
    """Ajusta dinámicamente el tamaño de fuente de un párrafo para que quepa en un área.

    Intenta encontrar el mayor tamaño de fuente posible sin que el párrafo
    exceda el alto disponible. Primero reduce la fuente si es necesario y
    luego la aumenta si hay espacio sobrante, dentro de los límites definidos.

    :param paragraph: El objeto `Paragraph` de ReportLab a ajustar.
    :type paragraph: Paragraph
    :param available_width: El ancho máximo disponible para el párrafo.
    :type available_width: float
    :param available_height: El alto máximo disponible para el párrafo.
    :type available_height: float
    :param style: El estilo del párrafo que se modificará.
    :type style: ParagraphStyle
    :param min_font_size: El tamaño de fuente mínimo permitido.
    :type min_font_size: int
    :param max_font_size: El tamaño de fuente máximo permitido.
    :type max_font_size: int
    :return: El objeto `Paragraph` con el tamaño de fuente ajustado.
    :rtype: Paragraph
    """
    w, h = paragraph.wrap(available_width, available_height)
    
    # Reducir si no cabe
    while h > available_height and style.fontSize > min_font_size:
        style.fontSize -= 1
        style.leading = style.fontSize * 1.2
        paragraph = Paragraph(paragraph.text, style)
        w, h = paragraph.wrap(available_width, available_height)
    
    # Aumentar si sobra espacio
    while h < available_height and style.fontSize < max_font_size:
        style.fontSize += 1
        style.leading = style.fontSize * 1.2
        new_paragraph = Paragraph(paragraph.text, style)
        w, h = new_paragraph.wrap(available_width, available_height)
        if h > available_height:
            style.fontSize -= 1
            style.leading = style.fontSize * 1.2
            break
        paragraph = new_paragraph
        
    return paragraph