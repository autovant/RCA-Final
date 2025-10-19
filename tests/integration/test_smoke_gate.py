"""Integration test ensuring the smoke suite blocks deployments on regressions."""

from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = pytest.mark.integration


def test_smoke_suite_exit_code_enforced():
    command = os.getenv("SMOKE_COMMAND")
    if not command:
        pytest.skip("Set SMOKE_COMMAND to run smoke gate integration test")

    expected_exit = int(os.getenv("SMOKE_EXPECT_EXIT", "1"))
    result = subprocess.run(command, shell=True)
    assert (
        result.returncode == expected_exit
    ), f"Smoke command returned {result.returncode}, expected {expected_exit}"
