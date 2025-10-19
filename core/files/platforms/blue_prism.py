"""Blue Prism platform parser."""

import re
from typing import Any, Dict, List, Optional

from .base import ParserResult, PlatformParser


class BluePrismParser(PlatformParser):
    """
    Parser for Blue Prism logs.
    
    Extracts:
    - Process names
    - Session IDs
    - Error codes and messages
    - Stage names
    - Execution timestamps
    """

    VERSION = "1.0.0"

    # Pattern examples (extend based on actual Blue Prism log formats)
    PROCESS_PATTERN = re.compile(r'Process[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    SESSION_PATTERN = re.compile(r'Session[:\s]+([a-f0-9\-]{36})', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'ERROR[:\s]+([^\n]+)', re.IGNORECASE)
    STAGE_PATTERN = re.compile(r'Stage[:\s]+"?([^"\n]+)"?', re.IGNORECASE)

    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """Extract Blue Prism entities from log files."""
        with self._measure_duration() as timer:
            entities: List[Dict[str, Any]] = []
            warnings: List[str] = []
            error = None

            try:
                for file_desc in files:
                    content = file_desc.get("content", "")
                    if not isinstance(content, str):
                        warnings.append(
                            f"Skipping non-text file: {file_desc.get('name', 'unknown')}"
                        )
                        continue

                    # Extract process names
                    for match in self.PROCESS_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "process",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract session IDs
                    for match in self.SESSION_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "session",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract errors
                    for match in self.ERROR_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "error",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract stage names
                    for match in self.STAGE_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "stage",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                # Deduplicate entities
                seen = set()
                unique_entities = []
                for entity in entities:
                    key = (
                        entity["entity_type"],
                        entity["value"],
                        entity.get("source_file"),
                    )
                    if key not in seen:
                        seen.add(key)
                        unique_entities.append(entity)

            except Exception as exc:
                error = f"Blue Prism parsing failed: {exc}"
                unique_entities = []

        return ParserResult(
            success=error is None,
            parser_version=self.VERSION,
            extracted_entities=unique_entities,
            duration_ms=timer.duration_ms,
            warnings=warnings,
            error=error,
        )
