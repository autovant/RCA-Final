"""Registry for platform-specific parsers."""

from typing import Optional

from .appian import AppianParser
from .automation_anywhere import AutomationAnywhereParser
from .base import PlatformParser
from .blue_prism import BluePrismParser
from .pega import PegaParser
from .uipath import UiPathParser

_PARSER_REGISTRY = {
    "blue_prism": BluePrismParser,
    "uipath": UiPathParser,
    "appian": AppianParser,
    "automation_anywhere": AutomationAnywhereParser,
    "pega": PegaParser,
}


def get_parser_for_platform(platform: str) -> Optional[PlatformParser]:
    """
    Retrieve parser instance for a given platform.
    
    Args:
        platform: Platform identifier (e.g., 'blue_prism', 'uipath')
    
    Returns:
        Instantiated parser or None if platform not supported
    """
    parser_class = _PARSER_REGISTRY.get(platform.lower())
    if parser_class is None:
        return None
    return parser_class()
