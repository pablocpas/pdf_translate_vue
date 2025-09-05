import os
import sys

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

sys.path.insert(0, os.path.abspath('../..'))


project = 'PDFTranslate'
copyright = '2025, Pablo Caño'
author = 'Pablo Caño'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',  # ¡Asegúrate de que esta línea esté aquí!
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon', # Opcional pero muy útil para otros estilos de docstring
]

latex_elements = {
    # ... otras opciones ...
    'preamble': r'''
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
''',
}

autodoc_mock_imports = [
    "boto3",
    "botocore",
    "celery",
    "doclayout_yolo",
    "fastapi",
    "matplotlib",
    "numpy",
    "openai",
    "pandas",
    "pdf2image",
    "PIL",
    "pydantic",
    "pydantic_settings",
    "pytesseract",
    "reportlab",
    "torch",
    "torchvision",
]


templates_path = ['_templates']
exclude_patterns = []

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
