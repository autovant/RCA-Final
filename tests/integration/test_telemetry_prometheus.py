"""Integration test that verifies telemetry metrics propagate to Prometheus/Thanos."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Iterable, Optional

import pytest

requests = pytest.importorskip("requests")

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Set {name} to execute telemetry integration tests")
    return value


def _maybe_run_upload_command(command: Optional[str]) -> None:
    if not command:
        return
    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)


def _wait_for_metric(base_url: str, query: str, *, timeout: int = 60, poll_interval: int = 5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{base_url}/api/v1/query",
            params={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "success" and payload.get("data", {}).get("result"):
            return payload
        time.sleep(poll_interval)
    pytest.fail(f"Timed out waiting for metric query to return data: {query}")


def _assert_thanos_rollup(thanos_url: str, query: str, *, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{thanos_url}/api/v1/query",
            params={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "success" and payload.get("data", {}).get("result"):
            return
        time.sleep(10)
    pytest.fail("Thanos did not return downsampled data within the expected window")


def test_pipeline_metrics_visible_in_prometheus():
    tenant_id = _require_env("TELEMETRY_TENANT_ID")
    prom_url = _require_env("PROMETHEUS_URL")
    upload_command = os.getenv("TELEMETRY_UPLOAD_COMMAND")
    stages_env = os.getenv("TELEMETRY_EXPECTED_STAGES", "ingest,chunk,embed,cache,storage")
    stages = [stage.strip() for stage in stages_env.split(",") if stage.strip()]
    timeout = int(os.getenv("TELEMETRY_METRIC_TIMEOUT", "60"))

    _maybe_run_upload_command(upload_command)

    for stage in stages:
        query = f'sum(rca_pipeline_stage_total{{tenant_id="{tenant_id}",stage="{stage}"}})'
        _wait_for_metric(prom_url, query, timeout=timeout)

    thanos_url = os.getenv("THANOS_QUERY_URL")
    if thanos_url:
        query = f'sum_over_time(rca_pipeline_stage_total{{tenant_id="{tenant_id}"}}[30m])'
        _assert_thanos_rollup(thanos_url, query)
