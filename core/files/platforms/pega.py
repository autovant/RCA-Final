"""Pega platform parser."""

import re
from typing import Any, Dict, List, Optional

from .base import ParserResult, PlatformParser


class PegaParser(PlatformParser):
    """
    Parser for Pega BPM logs.
    
    Extracts:
    - Case IDs
    - Flow names
    - Error messages
    - Ruleset names
    - Operator IDs
    """

    VERSION = "1.0.0"

    # Pattern examples (extend based on actual Pega log formats)
    CASE_PATTERN = re.compile(r'Case[:\s]+([A-Z0-9\-]+)', re.IGNORECASE)
    FLOW_PATTERN = re.compile(r'Flow[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'(?:ERROR|Exception)[:\s]+([^\n]+)', re.IGNORECASE)
    RULESET_PATTERN = re.compile(r'Ruleset[:\s]+"?([^"\n]+)"?', re.IGNORECASE)
    OPERATOR_PATTERN = re.compile(r'Operator[:\s]+"?([^"\n]+)"?', re.IGNORECASE)

    def parse(
        self,
        files: List[Dict[str, Any]],
        timeout_seconds: Optional[float] = None,
    ) -> ParserResult:
        """Extract Pega entities from log files."""
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

                    # Extract case IDs
                    for match in self.CASE_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "case",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract flows
                    for match in self.FLOW_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "flow",
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

                    # Extract rulesets
                    for match in self.RULESET_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "ruleset",
                                "value": match.group(1).strip(),
                                "source_file": file_desc.get("name"),
                            }
                        )

                    # Extract operators
                    for match in self.OPERATOR_PATTERN.finditer(content):
                        entities.append(
                            {
                                "entity_type": "operator",
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
                    error=f"Pega parsing failed: {exc}",
                )
