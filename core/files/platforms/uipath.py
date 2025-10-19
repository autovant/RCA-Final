"""UiPath platform parser."""

import re
from typing import Any, Dict, List, Optional

from .base import ParserResult, PlatformParser


class UiPathParser(PlatformParser):
    """
    Parser for UiPath logs.
    
    Extracts:
    - Workflow names
    - Robot names
    - Execution IDs
    - Error/exception messages
    - Queue items
    """

    VERSION = "1.0.0"

    # Pattern examples (extend based on actual UiPath log formats)
    WORKFLOW_PATTERN = re.compile(r'Workflow[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    ROBOT_PATTERN = re.compile(r'Robot[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    EXECUTION_PATTERN = re.compile(r'Execution[ID:\s]+([a-f0-9\-]{36})', re.IGNORECASE)
    EXCEPTION_PATTERN = re.compile(
        r'(?:Exception|Error)[:\s]+([^\n]+)', re.IGNORECASE
    )
    QUEUE_PATTERN = re.compile(r'Queue[:\s]+"?([^"\n]+)"?', re.IGNORECASE)

    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """Extract UiPath entities from log files."""
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

                    # Extract workflows
                    for match in self.WORKFLOW_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "workflow",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract robot names
                    for match in self.ROBOT_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "robot",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract execution IDs
                    for match in self.EXECUTION_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "execution",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract exceptions
                    for match in self.EXCEPTION_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "error",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract queue names
                    for match in self.QUEUE_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "queue",
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

            except Exception as exc:
                error = f"UiPath parsing failed: {exc}"
                unique_entities = []

        return ParserResult(
            success=error is None,
            parser_version=self.VERSION,
            extracted_entities=unique_entities,
            duration_ms=timer.duration_ms,
            warnings=warnings,
            error=error,
        )
