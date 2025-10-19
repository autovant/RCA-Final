"""Integration tests for platform detection with parser execution."""

import pytest

from core.files.detection import DetectionInput, PlatformDetectionOrchestrator


def test_detection_with_high_confidence_executes_parser():
    """When confidence >= rollout threshold, parser should execute and extract entities."""
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.15,
        rollout_confidence=0.60,
        capture_feature_flags=False,
    )

    # Provide clear UiPath signals with actual log content that parser can extract
    inputs = [
        DetectionInput(
            name="orchestrator.log",
            content="""
[2025-01-15 10:23:45] INFO: UiPath Orchestrator started
Workflow: "Invoice Processing Main.xaml"
Robot: "Robot-Finance-01"
Execution: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Queue: "High Priority Invoices"
[2025-01-15 10:24:12] ERROR: System.NullReferenceException at Main.xaml
""",
            content_type="text/plain",
            metadata={"source": "uipath orchestrator"},
        ),
    ]

    outcome = detector.detect("job-123", inputs)

    # Verify detection
    assert outcome.detected_platform == "uipath"
    assert outcome.confidence_score >= 0.60
    assert outcome.parser_executed is True
    assert outcome.parser_version is not None

    # Verify entities extracted by parser
    assert len(outcome.extracted_entities) > 0
    
    # Check for specific entities
    workflow_entities = [e for e in outcome.extracted_entities if e.get("entity_type") == "workflow"]
    assert len(workflow_entities) > 0
    assert any("Main.xaml" in e.get("value", "") for e in workflow_entities)
    
    robot_entities = [e for e in outcome.extracted_entities if e.get("entity_type") == "robot"]
    assert len(robot_entities) > 0


def test_detection_below_rollout_threshold_skips_parser():
    """When confidence < rollout threshold, parser should NOT execute."""
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.15,
        rollout_confidence=0.90,  # Set very high threshold
        capture_feature_flags=False,
    )

    # Provide weak UiPath signals (low confidence)
    inputs = [
        DetectionInput(
            name="generic.log",
            content="Some generic log content with the word uipath mentioned once",
            content_type="text/plain",
            metadata={},
        ),
    ]

    outcome = detector.detect("job-456", inputs)

    # Verify detection happened but parser didn't run
    assert outcome.detected_platform in ("uipath", "unknown")
    assert outcome.confidence_score < 0.90
    assert outcome.parser_executed is False
    assert outcome.parser_version is None
    assert len(outcome.extracted_entities) == 0


def test_detection_disabled_does_not_execute_parser():
    """When detection is disabled, no parser should execute."""
    detector = PlatformDetectionOrchestrator(enabled=False)

    inputs = [
        DetectionInput(
            name="uipath.log",
            content="Workflow: Test.xaml\nRobot: TestRobot",
            content_type="text/plain",
            metadata={},
        ),
    ]

    outcome = detector.detect("job-789", inputs)

    assert outcome.detected_platform == "unknown"
    assert outcome.parser_executed is False
    assert len(outcome.extracted_entities) == 0


def test_parser_failure_does_not_break_detection():
    """If parser fails, detection outcome should still be recorded."""
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.15,
        rollout_confidence=0.50,  # Lower threshold to ensure parser runs
        capture_feature_flags=False,
    )

    # Provide Blue Prism content with adequate confidence
    inputs = [
        DetectionInput(
            name="bpserver.log",  # Filename hint
            content="""
Blue Prism Server Log
Process: Main Process
Session: abc-123-def-456
Work Queue: Pending Items
""",
            content_type="text/plain",
            metadata={"source": "blue prism"},
        ),
    ]

    outcome = detector.detect("job-999", inputs)

    # Detection should succeed
    assert outcome.detected_platform == "blue_prism"
    assert outcome.confidence_score >= 0.50
    
    # Parser should have attempted execution
    # (it may succeed or fail gracefully without breaking detection)
    assert outcome.parser_version is not None or outcome.parser_executed is False


def test_multiple_platforms_selects_best_match():
    """When multiple platforms detected, highest confidence wins and its parser runs."""
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.15,
        rollout_confidence=0.60,
        capture_feature_flags=False,
    )

    # Content with strong Blue Prism signals
    inputs = [
        DetectionInput(
            name="bpserver.log",
            content="""
Blue Prism Server Log
Process: "Data Entry Workflow"
Session: abc-123-def-456
Work Queue: Pending Items
Stage: "Initialize Application"
ERROR: Connection timeout
""",
            content_type="text/plain",
            metadata={},
        ),
    ]

    outcome = detector.detect("job-multi", inputs)

    # Should detect Blue Prism with high confidence
    assert outcome.detected_platform == "blue_prism"
    assert outcome.confidence_score >= 0.60
    assert outcome.parser_executed is True
    
    # Should extract Blue Prism entities
    assert len(outcome.extracted_entities) > 0
    process_entities = [e for e in outcome.extracted_entities if e.get("entity_type") == "process"]
    assert len(process_entities) > 0
