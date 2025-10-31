"""
Pattern tester and presets for file watcher configurations.

Provides tools to validate patterns, test matching, and manage configuration presets.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


class PatternType(str, Enum):
    """Types of pattern matching supported."""
    GLOB = "glob"
    REGEX = "regex"
    EXTENSION = "extension"
    PREFIX = "prefix"
    SUFFIX = "suffix"


@dataclass
class PatternTestResult:
    """Result of pattern matching test."""
    
    matches: bool
    pattern: str
    pattern_type: PatternType
    test_path: str
    match_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PatternTester:
    """
    Test and validate file path patterns for watcher configurations.
    
    Supports multiple pattern types:
    - Glob patterns (*.log, **/*.txt)
    - Regular expressions
    - Simple extension matching (.csv)
    - Prefix/suffix matching
    """
    
    @staticmethod
    def test_pattern(
        pattern: str,
        test_path: str,
        pattern_type: PatternType = PatternType.GLOB,
    ) -> PatternTestResult:
        """
        Test if a pattern matches a given path.
        
        Args:
            pattern: Pattern to test
            test_path: Path to test against
            pattern_type: Type of pattern matching to use
        
        Returns:
            PatternTestResult with match status and details
        """
        try:
            if pattern_type == PatternType.GLOB:
                matches = fnmatch.fnmatch(test_path, pattern)
                return PatternTestResult(
                    matches=matches,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    match_details={"method": "fnmatch"}
                )
            
            elif pattern_type == PatternType.REGEX:
                compiled = re.compile(pattern)
                match = compiled.search(test_path)
                matches = match is not None
                details = None
                if match:
                    details = {
                        "method": "regex",
                        "groups": match.groups(),
                        "span": match.span(),
                    }
                return PatternTestResult(
                    matches=matches,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    match_details=details
                )
            
            elif pattern_type == PatternType.EXTENSION:
                # Normalize extension
                ext = pattern if pattern.startswith('.') else f'.{pattern}'
                matches = test_path.lower().endswith(ext.lower())
                return PatternTestResult(
                    matches=matches,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    match_details={"method": "extension", "normalized_ext": ext}
                )
            
            elif pattern_type == PatternType.PREFIX:
                matches = test_path.startswith(pattern)
                return PatternTestResult(
                    matches=matches,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    match_details={"method": "prefix"}
                )
            
            elif pattern_type == PatternType.SUFFIX:
                matches = test_path.endswith(pattern)
                return PatternTestResult(
                    matches=matches,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    match_details={"method": "suffix"}
                )
            
            else:
                return PatternTestResult(
                    matches=False,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    test_path=test_path,
                    error=f"Unsupported pattern type: {pattern_type}"
                )
        
        except Exception as exc:
            return PatternTestResult(
                matches=False,
                pattern=pattern,
                pattern_type=pattern_type,
                test_path=test_path,
                error=str(exc)
            )
    
    @staticmethod
    def test_multiple_paths(
        pattern: str,
        test_paths: List[str],
        pattern_type: PatternType = PatternType.GLOB,
    ) -> List[PatternTestResult]:
        """
        Test a pattern against multiple paths.
        
        Returns list of results for each path.
        """
        return [
            PatternTester.test_pattern(pattern, path, pattern_type)
            for path in test_paths
        ]
    
    @staticmethod
    def validate_pattern(
        pattern: str,
        pattern_type: PatternType = PatternType.GLOB,
    ) -> Dict[str, Any]:
        """
        Validate a pattern without testing against paths.
        
        Returns:
            Dict with validation status and any errors
        """
        result = {
            "valid": True,
            "pattern": pattern,
            "pattern_type": pattern_type,
            "errors": [],
            "warnings": [],
        }
        
        try:
            if pattern_type == PatternType.GLOB:
                # Test compilation with a dummy path
                fnmatch.fnmatch("test", pattern)
                
                # Check for common mistakes
                if "**" in pattern and "/" not in pattern:
                    result["warnings"].append(
                        "Pattern contains ** but no path separator"
                    )
            
            elif pattern_type == PatternType.REGEX:
                # Try to compile regex
                re.compile(pattern)
                
                # Check for common regex issues
                if pattern and pattern[0] not in ('^', '.*'):
                    result["warnings"].append(
                        "Regex doesn't start with ^ or .* - may not match paths"
                    )
            
            elif pattern_type == PatternType.EXTENSION:
                if not pattern:
                    result["valid"] = False
                    result["errors"].append("Extension pattern cannot be empty")
                elif pattern.count('.') > 1:
                    result["warnings"].append(
                        "Extension has multiple dots - this may be intentional"
                    )
            
            elif pattern_type in (PatternType.PREFIX, PatternType.SUFFIX):
                if not pattern:
                    result["valid"] = False
                    result["errors"].append(
                        f"{pattern_type.value} pattern cannot be empty"
                    )
        
        except re.error as exc:
            result["valid"] = False
            result["errors"].append(f"Invalid regex: {exc}")
        except Exception as exc:
            result["valid"] = False
            result["errors"].append(f"Validation error: {exc}")
        
        return result


@dataclass
class WatcherPreset:
    """Pre-configured watcher setup for common use cases."""
    
    name: str
    description: str
    patterns: List[str]
    pattern_type: PatternType = PatternType.GLOB
    processor: Optional[str] = None
    recursive: bool = True
    ignore_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_config(self) -> Dict[str, Any]:
        """Convert preset to watcher configuration dict."""
        return {
            "patterns": self.patterns,
            "pattern_type": self.pattern_type.value,
            "processor": self.processor,
            "recursive": self.recursive,
            "ignore_patterns": self.ignore_patterns,
            "metadata": {
                **self.metadata,
                "preset": self.name,
            }
        }


class PresetRegistry:
    """
    Registry of common watcher configuration presets.
    
    Provides pre-built configurations for common scenarios like:
    - Log file monitoring
    - CSV data ingestion
    - Archive extraction
    - Code repository watching
    """
    
    # Built-in presets
    PRESETS: Dict[str, WatcherPreset] = {
        "logs": WatcherPreset(
            name="logs",
            description="Monitor log files (.log, .txt)",
            patterns=["*.log", "*.txt"],
            pattern_type=PatternType.GLOB,
            processor="log_ingestion",
            ignore_patterns=["*.tmp", "*.swp"],
            metadata={"category": "logs"}
        ),
        
        "csv_data": WatcherPreset(
            name="csv_data",
            description="Monitor CSV data files",
            patterns=["*.csv"],
            pattern_type=PatternType.EXTENSION,
            processor="csv_ingestion",
            ignore_patterns=["*~", ".~lock.*"],
            metadata={"category": "data"}
        ),
        
        "archives": WatcherPreset(
            name="archives",
            description="Monitor and extract archive files",
            patterns=["*.zip", "*.tar.gz", "*.tgz", "*.tar"],
            pattern_type=PatternType.GLOB,
            processor="archive_extraction",
            recursive=True,
            metadata={"category": "archives"}
        ),
        
        "rpa_reports": WatcherPreset(
            name="rpa_reports",
            description="Monitor RPA execution reports",
            patterns=["*report*.xlsx", "*Report*.xlsx", "*.xlsx"],
            pattern_type=PatternType.GLOB,
            processor="rpa_ingestion",
            ignore_patterns=["~$*", "*.tmp"],
            metadata={"category": "rpa", "excel": True}
        ),
        
        "json_config": WatcherPreset(
            name="json_config",
            description="Monitor JSON configuration files",
            patterns=["*.json"],
            pattern_type=PatternType.EXTENSION,
            processor="config_reload",
            recursive=True,
            ignore_patterns=["node_modules/**", ".git/**"],
            metadata={"category": "config"}
        ),
        
        "images": WatcherPreset(
            name="images",
            description="Monitor image files",
            patterns=["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"],
            pattern_type=PatternType.GLOB,
            processor="image_processing",
            metadata={"category": "media"}
        ),
        
        "documents": WatcherPreset(
            name="documents",
            description="Monitor document files",
            patterns=["*.pdf", "*.docx", "*.xlsx", "*.pptx"],
            pattern_type=PatternType.GLOB,
            processor="document_ingestion",
            ignore_patterns=["~$*"],
            metadata={"category": "documents"}
        ),
    }
    
    def __init__(self):
        # Custom presets added at runtime
        self._custom_presets: Dict[str, WatcherPreset] = {}
    
    def get_preset(self, name: str) -> Optional[WatcherPreset]:
        """Get a preset by name (checks custom first, then built-in)."""
        if name in self._custom_presets:
            return self._custom_presets[name]
        return self.PRESETS.get(name)
    
    def list_presets(
        self,
        category: Optional[str] = None,
        include_custom: bool = True,
    ) -> List[WatcherPreset]:
        """
        List available presets.
        
        Args:
            category: Filter by metadata category
            include_custom: Include custom presets
        
        Returns:
            List of matching presets
        """
        presets = list(self.PRESETS.values())
        
        if include_custom:
            presets.extend(self._custom_presets.values())
        
        if category:
            presets = [
                p for p in presets
                if p.metadata.get("category") == category
            ]
        
        return presets
    
    def register_preset(self, preset: WatcherPreset) -> None:
        """Register a custom preset."""
        if preset.name in self.PRESETS:
            logger.warning(
                "Registering custom preset '%s' shadows built-in preset",
                preset.name
            )
        
        self._custom_presets[preset.name] = preset
        logger.info("Registered custom watcher preset: %s", preset.name)
    
    def unregister_preset(self, name: str) -> bool:
        """Unregister a custom preset. Returns True if removed."""
        if name in self._custom_presets:
            del self._custom_presets[name]
            logger.info("Unregistered custom watcher preset: %s", name)
            return True
        return False
    
    def get_categories(self) -> Set[str]:
        """Get all available preset categories."""
        categories = set()
        for preset in self.PRESETS.values():
            if "category" in preset.metadata:
                categories.add(preset.metadata["category"])
        for preset in self._custom_presets.values():
            if "category" in preset.metadata:
                categories.add(preset.metadata["category"])
        return categories


# Global singleton
_preset_registry: Optional[PresetRegistry] = None


def get_preset_registry() -> PresetRegistry:
    """Get or create the global preset registry."""
    global _preset_registry
    if _preset_registry is None:
        _preset_registry = PresetRegistry()
    return _preset_registry
