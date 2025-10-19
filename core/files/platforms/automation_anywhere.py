"""Automation Anywhere platform parser."""

import re
from typing import Any, Dict, List, Optional

from .base import ParserResult, PlatformParser


class AutomationAnywhereParser(PlatformParser):
    """
    Parser for Automation Anywhere logs.
    
    Extracts:
    - Bot names
    - Task names
    - Error messages
    - Bot runner IDs
    - Device names
    """

    VERSION = "1.0.0"

    # Pattern examples (extend based on actual AA log formats)
    # Order matters: check Bot Runner before Bot to avoid overlap
    RUNNER_PATTERN = re.compile(r'Bot Runner[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    BOT_PATTERN = re.compile(r'\bBot[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    TASK_PATTERN = re.compile(r'Task[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'(?:ERROR|Exception)[:\s]+([^\n]+)', re.IGNORECASE)
    DEVICE_PATTERN = re.compile(r'Device[:\s]+"?([^"\n]+)"?', re.IGNORECASE)

    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """Extract Automation Anywhere entities from log files."""
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

                    # Extract bot runners FIRST (before bots to avoid overlap)
                    runner_positions = set()
                    for match in self.RUNNER_PATTERN.finditer(content):
                        runner_positions.add(match.start())
                        entities.append(
                            {
                                "entity_type": "bot_runner",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract bot names (skip if part of "Bot Runner")
                    for match in self.BOT_PATTERN.finditer(content):
                        # Skip if this match is part of a "Bot Runner" match
                        if match.start() not in runner_positions:
                            entities.append(
                                {
                                    "entity_type": "bot",
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

                    # Extract device names
                    for match in self.DEVICE_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "device",
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
                error = f"Automation Anywhere parsing failed: {exc}"
                unique_entities = []

        return ParserResult(
            success=error is None,
            parser_version=self.VERSION,
            extracted_entities=unique_entities,
            duration_ms=timer.duration_ms,
            warnings=warnings,
            error=error,
        )
