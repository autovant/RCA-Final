"""Platform-specific log parsers for RPA systems."""

from .base import PlatformParser, ParserResult
from .registry import get_parser_for_platform

__all__ = [
    "PlatformParser",
    "ParserResult",
    "get_parser_for_platform",
]
