"""Unit tests for platform-specific parsers."""

import pytest

from core.files.platforms import (
    ParserResult,
    get_parser_for_platform,
)
from core.files.platforms.appian import AppianParser
from core.files.platforms.automation_anywhere import AutomationAnywhereParser
from core.files.platforms.base import PlatformParser
from core.files.platforms.blue_prism import BluePrismParser
from core.files.platforms.pega import PegaParser
from core.files.platforms.uipath import UiPathParser


def test_get_parser_for_unknown_platform_returns_none():
    """Unknown platforms should return None."""
    parser = get_parser_for_platform("nonexistent_platform")
    assert parser is None


def test_get_parser_for_blue_prism():
    """Should return BluePrismParser instance."""
    parser = get_parser_for_platform("blue_prism")
    assert isinstance(parser, BluePrismParser)
    assert parser.VERSION == "1.0.0"


def test_get_parser_for_uipath():
    """Should return UiPathParser instance."""
    parser = get_parser_for_platform("uipath")
    assert isinstance(parser, UiPathParser)
    assert parser.VERSION == "1.0.0"


def test_get_parser_for_appian():
    """Should return AppianParser instance."""
    parser = get_parser_for_platform("appian")
    assert isinstance(parser, AppianParser)
    assert parser.VERSION == "1.0.0"


def test_get_parser_for_automation_anywhere():
    """Should return AutomationAnywhereParser instance."""
    parser = get_parser_for_platform("automation_anywhere")
    assert isinstance(parser, AutomationAnywhereParser)
    assert parser.VERSION == "1.0.0"


def test_get_parser_for_pega():
    """Should return PegaParser instance."""
    parser = get_parser_for_platform("pega")
    assert isinstance(parser, PegaParser)
    assert parser.VERSION == "1.0.0"


def test_blue_prism_parser_extracts_process_names():
    """BluePrismParser should identify process names from log content."""
    parser = BluePrismParser()
    files = [
        {
            "name": "test.log",
            "content": """
Process: "Data Entry Workflow"
Session: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Stage: "Initialize Application"
ERROR: Connection timeout occurred
Process: "Invoice Processing"
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    assert result.parser_version == "1.0.0"
    assert result.duration_ms is not None
    assert result.duration_ms > 0

    # Check extracted entities
    entities = result.extracted_entities
    assert len(entities) > 0

    process_entities = [e for e in entities if e["entity_type"] == "process"]
    assert len(process_entities) == 2
    assert any(e["value"] == "Data Entry Workflow" for e in process_entities)
    assert any(e["value"] == "Invoice Processing" for e in process_entities)

    session_entities = [e for e in entities if e["entity_type"] == "session"]
    assert len(session_entities) == 1

    error_entities = [e for e in entities if e["entity_type"] == "error"]
    assert len(error_entities) == 1


def test_uipath_parser_extracts_workflow_names():
    """UiPathParser should identify workflow and robot names."""
    parser = UiPathParser()
    files = [
        {
            "name": "robot.log",
            "content": """
Workflow: "Main.xaml"
Robot: "Robot_01"
Execution: f1e2d3c4-b5a6-7980-1234-567890abcdef
Queue: "High Priority Items"
Exception: System.NullReferenceException at Main.xaml
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    entities = result.extracted_entities

    workflow_entities = [e for e in entities if e["entity_type"] == "workflow"]
    assert len(workflow_entities) == 1
    assert workflow_entities[0]["value"] == "Main.xaml"

    robot_entities = [e for e in entities if e["entity_type"] == "robot"]
    assert len(robot_entities) == 1

    queue_entities = [e for e in entities if e["entity_type"] == "queue"]
    assert len(queue_entities) == 1


def test_appian_parser_extracts_process_models():
    """AppianParser should identify process models and tasks."""
    parser = AppianParser()
    files = [
        {
            "name": "appian.log",
            "content": """
Process Model: "Employee Onboarding"
Task: "Review Documentation"
User: "john.doe@example.com"
Instance: 12345
ERROR: Invalid form submission
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    entities = result.extracted_entities

    process_entities = [e for e in entities if e["entity_type"] == "process_model"]
    assert len(process_entities) == 1
    assert process_entities[0]["value"] == "Employee Onboarding"

    task_entities = [e for e in entities if e["entity_type"] == "task"]
    assert len(task_entities) == 1


def test_automation_anywhere_parser_extracts_bot_names():
    """AutomationAnywhereParser should identify bot and task names."""
    parser = AutomationAnywhereParser()
    files = [
        {
            "name": "aa.log",
            "content": """
Bot: "Invoice Processing Bot"
Task: "Extract PDF Data"
Bot Runner: "Runner-Production-01"
Device: "WIN-SERVER-01"
ERROR: File not found exception
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    entities = result.extracted_entities

    bot_entities = [e for e in entities if e["entity_type"] == "bot"]
    assert len(bot_entities) == 1
    assert bot_entities[0]["value"] == "Invoice Processing Bot"

    runner_entities = [e for e in entities if e["entity_type"] == "bot_runner"]
    assert len(runner_entities) == 1


def test_pega_parser_extracts_case_ids():
    """PegaParser should identify case IDs and flows."""
    parser = PegaParser()
    files = [
        {
            "name": "pega.log",
            "content": """
Case: CLAIM-12345
Flow: "Claims Processing"
Ruleset: "ClaimsApp:01-01-05"
Operator: "claims.processor"
Exception: Rule resolution failed
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    entities = result.extracted_entities

    case_entities = [e for e in entities if e["entity_type"] == "case"]
    assert len(case_entities) == 1
    assert case_entities[0]["value"] == "CLAIM-12345"

    flow_entities = [e for e in entities if e["entity_type"] == "flow"]
    assert len(flow_entities) == 1


def test_parser_handles_empty_files():
    """Parsers should handle empty file lists gracefully."""
    parser = UiPathParser()
    result = parser.parse([])

    assert result.success is True
    assert len(result.extracted_entities) == 0
    assert len(result.warnings) == 0


def test_parser_handles_non_text_content():
    """Parsers should skip non-text files and emit warnings."""
    parser = BluePrismParser()
    files = [
        {
            "name": "binary.dat",
            "content": b"\x00\x01\x02\x03",  # Binary content
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    assert len(result.extracted_entities) == 0
    assert len(result.warnings) > 0
    assert "non-text" in result.warnings[0].lower()


def test_parser_deduplicates_entities():
    """Parsers should deduplicate identical entities."""
    parser = UiPathParser()
    files = [
        {
            "name": "log1.txt",
            "content": """
Workflow: "Main.xaml"
Workflow: "Main.xaml"
Robot: "Robot_01"
Robot: "Robot_01"
""",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    workflow_entities = [e for e in result.extracted_entities if e["entity_type"] == "workflow"]
    assert len(workflow_entities) == 1  # Deduped

    robot_entities = [e for e in result.extracted_entities if e["entity_type"] == "robot"]
    assert len(robot_entities) == 1  # Deduped


def test_parser_result_includes_source_file():
    """Extracted entities should reference their source file."""
    parser = AppianParser()
    files = [
        {
            "name": "server1.log",
            "content": "Process Model: Test Process",
            "metadata": {},
        }
    ]

    result = parser.parse(files)

    assert result.success is True
    assert len(result.extracted_entities) > 0
    entity = result.extracted_entities[0]
    assert entity["source_file"] == "server1.log"
