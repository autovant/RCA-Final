"""Appian platform parser."""

import re
from typing import Any, Dict, List, Optional

from .base import ParserResult, PlatformParser


class AppianParser(PlatformParser):
    """
    Parser for Appian BPM logs.
    
    Extracts:
    - Process model names
    - Task names
    - Error messages
    - User IDs
    - Process instance IDs
    """

    VERSION = "1.0.0"

    # Pattern examples (extend based on actual Appian log formats)
    PROCESS_MODEL_PATTERN = re.compile(
        r'Process Model[:\s]+"?([^"\n]+)"?', re.IGNORECASE
    )
    TASK_PATTERN = re.compile(r'Task[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'ERROR[:\s]+([^\n]+)', re.IGNORECASE)
    USER_PATTERN = re.compile(r'User[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    INSTANCE_PATTERN = re.compile(r'Instance[:\s]+([0-9]+)', re.IGNORECASE)

    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """Extract Appian entities from log files."""
        with self._measure_duration() as timer:
            try:
                entities: List[Dict[str, Any]] = []
                warnings: List[str] = []

                for file_desc in files:
                    content = file_desc.get("content", "")
                    if not isinstance(content, str):
                        warnings.append(
                            f"Skipping non-text file: {file_desc.get('name', 'unknown')}"
                        )
                        continue

                    # Extract process models
                    for match in self.PROCESS_MODEL_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "process_model",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract tasks
                    for match in self.TASK_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "task",
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

                    # Extract users
                    for match in self.USER_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "user",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract instance IDs
                    for match in self.INSTANCE_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "instance",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                # Deduplicate
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

                return ParserResult(
                    success=True,
                    parser_version=self.VERSION,
                    extracted_entities=unique_entities,
                    duration_ms=timer.duration_ms,
                    warnings=warnings,
                )

            except Exception as exc:
                return ParserResult(
                    success=False,
                    parser_version=self.VERSION,
                    duration_ms=timer.duration_ms,
                    error=f"Appian parsing failed: {exc}",
                )
