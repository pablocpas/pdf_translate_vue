"""
Font registry service.

This module handles font registration and management,
extracting the font logic from the original processor.py.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

from shared.models.exceptions import FontError
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FontRegistry:
    """
    Registry for managing font registration and availability.
    
    This class consolidates the font registration logic that was
    scattered in the original processor.py file.
    """
    
    def __init__(self):
        """Initialize the font registry."""
        self._registered_fonts: Dict[str, Dict[str, Any]] = {}
        self._fonts_dir = self._get_fonts_directory()
    
    def _get_fonts_directory(self) -> Path:
        """
        Get the fonts directory path.
        
        Returns:
            Path: Path to fonts directory
        """
        # Get fonts directory relative to this file
        current_dir = Path(__file__).parent
        fonts_dir = current_dir / "assets"
        
        # Ensure fonts directory exists
        fonts_dir.mkdir(exist_ok=True)
        
        return fonts_dir
    
    def register_all_fonts(self) -> None:
        """
        Register all available fonts.
        
        This method replaces the font registration code that was
        embedded in the original processor initialization.
        """
        logger.info("Registering fonts...")
        
        # Register OpenSans fonts
        self._register_opensans_fonts()
        
        # Register CJK fonts (if available)
        self._register_cjk_fonts()
        
        logger.info(f"Font registration completed: {len(self._registered_fonts)} fonts registered")
    
    def _register_opensans_fonts(self) -> None:
        """Register OpenSans font family."""
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Register OpenSans Regular
            regular_path = self._fonts_dir / "OpenSans-Regular.ttf"
            if regular_path.exists():
                try:
                    pdfmetrics.registerFont(TTFont('OpenSans', str(regular_path)))
                    self._registered_fonts['OpenSans'] = {
                        'path': str(regular_path),
                        'family': 'OpenSans',
                        'style': 'Regular',
                        'available': True,
                        'type': 'TTF'
                    }
                    logger.debug("OpenSans Regular font registered successfully")
                except Exception as e:
                    logger.warning(f"Failed to register OpenSans Regular: {str(e)}")
            else:
                logger.warning(f"OpenSans Regular font file not found: {regular_path}")
            
            # Register OpenSans Bold
            bold_path = self._fonts_dir / "OpenSans-Bold.ttf"
            if bold_path.exists():
                try:
                    pdfmetrics.registerFont(TTFont('OpenSans-Bold', str(bold_path)))
                    self._registered_fonts['OpenSans-Bold'] = {
                        'path': str(bold_path),
                        'family': 'OpenSans',
                        'style': 'Bold',
                        'available': True,
                        'type': 'TTF'
                    }
                    logger.debug("OpenSans Bold font registered successfully")
                except Exception as e:
                    logger.warning(f"Failed to register OpenSans Bold: {str(e)}")
            else:
                logger.warning(f"OpenSans Bold font file not found: {bold_path}")
                
        except ImportError as e:
            logger.error(f"ReportLab not available for font registration: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to register OpenSans fonts: {str(e)}")
    
    def _register_cjk_fonts(self) -> None:
        """Register CJK (Chinese, Japanese, Korean) fonts."""
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            
            # CJK fonts available in ReportLab
            cjk_fonts = [
                ('HeiseiMin-W3', 'Japanese'),
                ('HYSMyeongJo-Medium', 'Korean'),
                ('STSong-Light', 'Chinese')
            ]
            
            for font_name, language in cjk_fonts:
                try:
                    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                    self._registered_fonts[font_name] = {
                        'path': None,  # CID fonts don't have file paths
                        'family': font_name,
                        'style': 'Regular',
                        'available': True,
                        'type': 'CID',
                        'language': language
                    }
                    logger.debug(f"CJK font registered: {font_name} ({language})")
                except Exception as e:
                    logger.warning(f"Failed to register CJK font {font_name}: {str(e)}")
                    self._registered_fonts[font_name] = {
                        'path': None,
                        'family': font_name,
                        'style': 'Regular',
                        'available': False,
                        'type': 'CID',
                        'language': language,
                        'error': str(e)
                    }
                    
        except ImportError as e:
            logger.warning(f"ReportLab CID fonts not available: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to register CJK fonts: {str(e)}")
    
    def get_font_info(self, font_name: str) -> Dict[str, Any]:
        """
        Get information about a registered font.
        
        Args:
            font_name: Name of the font
            
        Returns:
            Dict[str, Any]: Font information
        """
        if font_name in self._registered_fonts:
            return self._registered_fonts[font_name].copy()
        else:
            return {
                'path': None,
                'family': font_name,
                'style': 'Unknown',
                'available': False,
                'type': 'Unknown',
                'error': 'Font not registered'
            }
    
    def is_font_available(self, font_name: str) -> bool:
        """
        Check if a font is available.
        
        Args:
            font_name: Name of the font
            
        Returns:
            bool: True if font is available
        """
        font_info = self.get_font_info(font_name)
        return font_info.get('available', False)
    
    def list_available_fonts(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available fonts.
        
        Returns:
            List[Dict[str, Any]]: List of available font information
        """
        available_fonts = []
        
        for font_name, font_info in self._registered_fonts.items():
            if font_info.get('available', False):
                font_copy = font_info.copy()
                font_copy['name'] = font_name
                available_fonts.append(font_copy)
        
        return available_fonts
    
    def list_fonts_by_type(self, font_type: str) -> List[str]:
        """
        Get fonts by type (TTF, CID, etc.).
        
        Args:
            font_type: Type of fonts to list
            
        Returns:
            List[str]: List of font names
        """
        matching_fonts = []
        
        for font_name, font_info in self._registered_fonts.items():
            if (font_info.get('type', '').upper() == font_type.upper() and 
                font_info.get('available', False)):
                matching_fonts.append(font_name)
        
        return matching_fonts
    
    def get_fonts_for_language(self, language: str) -> List[str]:
        """
        Get fonts suitable for a specific language.
        
        Args:
            language: Language identifier
            
        Returns:
            List[str]: List of suitable font names
        """
        suitable_fonts = []
        
        for font_name, font_info in self._registered_fonts.items():
            if not font_info.get('available', False):
                continue
                
            # Check if font is specifically for this language
            if font_info.get('language', '').lower() == language.lower():
                suitable_fonts.append(font_name)
            # OpenSans is suitable for most Latin-based languages
            elif font_name.startswith('OpenSans') and language.lower() in [
                'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'pl', 'ru', 'sv',
                'da', 'no', 'fi', 'hu', 'cs', 'sk', 'sl', 'hr', 'bg', 'ro',
                'el', 'tr', 'sw'
            ]:
                suitable_fonts.append(font_name)
        
        # If no specific fonts found, return OpenSans as fallback
        if not suitable_fonts and self.is_font_available('OpenSans'):
            suitable_fonts.append('OpenSans')
        
        return suitable_fonts
    
    def cleanup(self) -> None:
        """
        Clean up font registry resources.
        
        This method can be called during application shutdown
        to clean up any font-related resources.
        """
        logger.info("Cleaning up font registry...")
        # In this implementation, there's nothing specific to clean up
        # But this method is here for consistency and future extensions
        logger.debug("Font registry cleanup completed")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the font registry.
        
        Returns:
            Dict[str, Any]: Registry statistics
        """
        total_fonts = len(self._registered_fonts)
        available_fonts = sum(
            1 for info in self._registered_fonts.values() 
            if info.get('available', False)
        )
        
        font_types = {}
        for info in self._registered_fonts.values():
            font_type = info.get('type', 'Unknown')
            font_types[font_type] = font_types.get(font_type, 0) + 1
        
        return {
            'total_fonts': total_fonts,
            'available_fonts': available_fonts,
            'unavailable_fonts': total_fonts - available_fonts,
            'font_types': font_types,
            'fonts_directory': str(self._fonts_dir)
        }