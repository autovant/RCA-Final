"""Tests for the job processor orchestration logic."""

from __future__ import annotations

from types import SimpleNamespace
import pytest

pytest.importorskip("aiofiles")

from core.jobs.processor import FileDescriptor, FileSummary, JobProcessor


class StubJobService:
    def __init__(self):
        self.events = []

    async def create_job_event(self, job_id: str, event_type: str, data=None, session=None):
        self.events.append((job_id, event_type, data or {}))


class StubProcessor(JobProcessor):
    def __init__(self, descriptors, summaries, job_service):
        super().__init__(job_service)
        self._descriptors = descriptors
        self._summaries = summaries

    async def _list_job_files(self, job_id: str):
        return self._descriptors

    async def _process_single_file(self, job, descriptor: FileDescriptor):
        await self._job_service.create_job_event(
            job.id,
            "file-processing-started",
            {"file_id": descriptor.id},
        )
        summary = self._summaries[descriptor.id]
        await self._job_service.create_job_event(
            job.id,
            "file-processing-completed",
            {"file_id": descriptor.id, "chunks": summary.chunk_count},
        )
        return summary

    async def _generate_embeddings(self, texts):
        return [[1.0] * max(1, len(texts)) for _ in texts]

    async def _run_llm_analysis(self, job, summaries, mode):
        return {"summary": f"{mode}-analysis", "provider": "stub", "model": "stub"}


def _summary(file_id: str, filename: str, errors: int, warnings: int) -> FileSummary:
    return FileSummary(
        file_id=file_id,
        filename=filename,
        checksum="checksum",
        file_size=42,
        content_type="text/plain",
        line_count=10,
        error_count=errors,
        warning_count=warnings,
        critical_count=0,
        info_count=10 - errors - warnings,
        sample_head=["line1"],
        sample_tail=["line10"],
        top_keywords=["error", "info"],
        chunk_count=1,
    )


@pytest.mark.asyncio
async def test_process_rca_analysis_compiles_summary():
    descriptors = [
        FileDescriptor(
            id="file-1",
            path="/tmp/file-1.log",
            name="file-1.log",
            checksum="checksum",
            content_type="text/plain",
            metadata=None,
            size_bytes=42,
        )
    ]
    summaries = {"file-1": _summary("file-1", "file-1.log", errors=2, warnings=1)}
    job_service = StubJobService()
    processor = StubProcessor(descriptors, summaries, job_service)

    job = SimpleNamespace(
        id="job-1",
        job_type="rca_analysis",
        provider="stub",
        model="stub",
        input_manifest={},
    )
    result = await processor.process_rca_analysis(job)

    assert result["analysis_type"] == "rca_analysis"
    assert result["metrics"]["errors"] == 2
    assert result["llm"]["summary"] == "rca_analysis-analysis"
    assert len(processor._job_service.events) == 6  # ingestion + llm phases + file hooks


@pytest.mark.asyncio
async def test_process_log_analysis_reports_suspected_error_logs():
    descriptors = [
        FileDescriptor(
            id="file-2",
            path="/tmp/file-2.log",
            name="errors.log",
            checksum="checksum",
            content_type="text/plain",
            metadata=None,
            size_bytes=21,
        )
    ]
    summaries = {"file-2": _summary("file-2", "errors.log", errors=1, warnings=0)}
    job_service = StubJobService()
    processor = StubProcessor(descriptors, summaries, job_service)

    job = SimpleNamespace(
        id="job-2",
        job_type="log_analysis",
        provider="stub",
        model="stub",
        input_manifest={},
    )

    result = await processor.process_log_analysis(job)

    assert result["analysis_type"] == "log_analysis"
    assert result["suspected_error_logs"] == ["errors.log"]
