"""Tests for heuristic platform detection orchestration."""

from __future__ import annotations

import pytest

from core.files.detection import DetectionInput, PlatformDetectionOrchestrator


def _make_input(name: str, content: str, metadata: dict[str, str] | None = None) -> DetectionInput:
    return DetectionInput(name=name, content=content, metadata=metadata or {})


def test_detection_disabled_returns_unknown():
    detector = PlatformDetectionOrchestrator(enabled=False)
    inputs = [_make_input("robot.log", "UiPath robot executor initialised")]

    outcome = detector.detect(job_id="job-001", inputs=inputs)

    assert outcome.detected_platform == "unknown"
    assert outcome.confidence_score == pytest.approx(0.0)
    assert outcome.feature_flag_snapshot.get("platform_detection_enabled") is False
    assert outcome.parser_executed is False


def test_detection_identifies_uipath_with_high_confidence():
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.15,
        rollout_confidence=0.65,
    )
    inputs = [
        _make_input(
            "robot_execution.log",
            "UiPath Orchestrator dispatched Robot Executor for XAML workflow",
            metadata={"platform": "UiPath"},
        )
    ]

    outcome = detector.detect(job_id="job-uipath", inputs=inputs)

    assert outcome.detected_platform == "uipath"
    assert outcome.confidence_score >= 0.65
    assert outcome.parser_executed is True


def test_detection_below_rollout_threshold_still_reports_platform():
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        min_confidence=0.1,
        rollout_confidence=0.9,
    )
    inputs = [
        _make_input(
            "control-room.log",
            "Automation Anywhere bot runner heartbeat",
        )
    ]

    outcome = detector.detect(job_id="job-aa", inputs=inputs)

    assert outcome.detected_platform == "automation_anywhere"
    assert outcome.confidence_score < 0.9
    assert outcome.parser_executed is False


def test_feature_flag_snapshot_can_be_suppressed():
    detector = PlatformDetectionOrchestrator(
        enabled=True,
        capture_feature_flags=False,
    )
    inputs = [_make_input("appian.txt", "Appian process model event")]

    outcome = detector.detect(job_id="job-appian", inputs=inputs)

    assert outcome.feature_flag_snapshot == {}
    assert outcome.detected_platform in {"appian", "unknown"}