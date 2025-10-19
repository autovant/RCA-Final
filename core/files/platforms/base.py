"""Base parser interface for platform-specific entity extraction."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParserResult:
    """
    Normalized output from a platform-specific parser.
    
    Attributes:
        success: Whether parsing completed successfully
        parser_version: Version identifier for the parser
        extracted_entities: Platform-specific entities (process names, errors, etc.)
        duration_ms: Time taken for parsing in milliseconds
        warnings: Non-fatal issues encountered during parsing
        error: Fatal error message if parsing failed
    """

    success: bool
    parser_version: str
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class PlatformParser(ABC):
    """
    Abstract base class for platform-specific log parsers.
    
    Parsers extract structured entities from log text to enrich RCA insights.
    Common entities include:
    - Process/workflow names
    - Error codes and messages
    - Execution timestamps
    - Robot/agent identifiers
    - Environment/queue information
    """

    VERSION = "1.0.0"  # Override in subclasses

    @abstractmethod
    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """
        Parse platform-specific entities from file content.
        
        Args:
            files: List of file descriptors with 'name', 'content', 'metadata' keys
            timeout_seconds: Maximum parsing time (None for no limit)
        
        Returns:
            ParserResult with extracted entities and status
        """
        pass

    def _measure_duration(self):
        """Context manager for timing parser execution."""
        return _TimingContext()


class _TimingContext:
    """Helper for measuring parser duration."""

    def __init__(self):
        self.start_time = None
        self.duration_ms = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        if self.start_time is not None:
            self.duration_ms = (end_time - self.start_time) * 1000.0
        return False
