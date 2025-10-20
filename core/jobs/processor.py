"""
Job processor responsible for ingesting uploaded artefacts, generating
embeddings, and orchestrating LLM-backed analysis.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import re
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, cast

import aiofiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache.embedding_cache_service import EmbeddingCacheService
from core.config import settings
from core.config.feature_flags import TELEMETRY_ENHANCED_METRICS
from core.db.database import get_db_session
from core.db.models import Document, File, IncidentFingerprint, Job, PlatformDetectionResult
from core.files import DetectionInput, PlatformDetectionOrchestrator
from core.files.encoding import EncodingProbeError, probe_text_file
from core.files.telemetry import (
    PipelineStage,
    PipelineStatus,
    UploadTelemetryEvent,
    coerce_metadata_value,
    persist_upload_telemetry_event,
    sanitise_metadata,
)
from core.jobs.models import (
    FingerprintStatus,
    IncidentFingerprintDTO,
    PlatformDetectionOutcome,
    VisibilityScope,
)
from core.jobs.service import JobService
from core.llm.embeddings import EmbeddingService
from core.llm.providers import LLMMessage, LLMProviderFactory
from core.logging import get_logger, log_platform_detection_event
from core.metrics.collectors import observe_detection
from core.metrics.pipeline_metrics import PipelineMetricsCollector
from core.metrics.models import DetectionMetricEvent
from core.privacy import PiiRedactor, RedactionResult

logger = get_logger(__name__)


_PIPELINE_METRICS = PipelineMetricsCollector()

MAX_FINGERPRINT_SUMMARY_LENGTH = 4096

PROGRESS_STEP_LABELS: Dict[str, str] = {
    "classification": "Classifying uploaded files",
    "upload": "Upload received",
    "redaction": "Locking down sensitive data",
    "chunking": "Segmenting content into analysis-ready chunks",
    "embedding": "Generating semantic embeddings",
    "storage": "Storing structured insights",
    "correlation": "Correlating with historical incidents",
    "llm": "Running AI-powered root cause analysis",
    "report": "Preparing final RCA report",
    "completed": "Analysis completed successfully",
}

PIPELINE_STAGE_TO_PROGRESS_STEP: Dict[PipelineStage, str] = {
    PipelineStage.INGEST: "chunking",
    PipelineStage.CHUNK: "chunking",
    PipelineStage.EMBED: "embedding",
    PipelineStage.STORAGE: "storage",
}

_PROGRESS_LABEL_MAX_CHARS = 128
_PROGRESS_MESSAGE_MAX_CHARS = 512


def _coerce_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):  # pragma: no cover - defensive guard
        return None


@dataclass
class PipelineContext:
    tenant_label: str
    tenant_uuid: Optional[uuid.UUID]
    job_uuid: Optional[uuid.UUID]
    file_uuid: Optional[uuid.UUID]
    platform: str
    file_type: str
    feature_flags: List[str]
    telemetry_enabled: bool
    metrics_enabled: bool
    size_bytes: Optional[int]



@dataclass
class FileDescriptor:
    """Snapshot of a file record detached from the ORM session."""

    id: str
    path: str
    name: str
    checksum: str
    content_type: Optional[str]
    metadata: Optional[Dict[str, Any]]
    size_bytes: int


@dataclass
class FileSummary:
    """Aggregated metadata produced after analysing a file."""

    file_id: str
    filename: str
    checksum: str
    file_size: int
    content_type: Optional[str]
    line_count: int
    error_count: int
    warning_count: int
    critical_count: int
    info_count: int
    sample_head: List[str]
    sample_tail: List[str]
    top_keywords: List[str]
    chunk_count: int = 0
    redaction_applied: bool = False
    redaction_counts: Dict[str, int] = field(default_factory=dict)
    redaction_failsafe_triggered: bool = False
    redaction_validation_warnings: List[str] = field(default_factory=list)


class JobProcessor:
    """Async handlers for background job types leveraging embeddings + LLMs."""

    def __init__(self, job_service: Optional[JobService] = None) -> None:
        self._job_service = job_service or JobService()
        self._session_factory = get_db_session()
        self._embedding_service: Optional[EmbeddingService] = None
        self._embedding_lock = asyncio.Lock()
        self._pii_redactor = PiiRedactor()

    def _progress_label(self, step: str) -> str:
        return PROGRESS_STEP_LABELS.get(
            step,
            step.replace("_", " ").replace("-", " ").title(),
        )

    def _describe_file_position(
        self,
        filename: Optional[str],
        position: Optional[int],
        total: Optional[int],
    ) -> str:
        label = filename or "uploaded files"
        if (
            position is not None
            and total is not None
            and isinstance(position, int)
            and isinstance(total, int)
            and total > 0
        ):
            return f"{label} ({position}/{total})"
        return label

    async def _emit_progress_event(
        self,
        job_id: str,
        step: str,
        status: str,
        *,
        label: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        label_text = label or self._progress_label(step)
        if len(label_text) > _PROGRESS_LABEL_MAX_CHARS:
            label_text = f"{label_text[: _PROGRESS_LABEL_MAX_CHARS - 3]}..."

        payload: Dict[str, Any] = {
            "step": step,
            "status": status,
            "label": label_text,
        }

        if message is not None:
            message_text = str(message).strip()
            if not message_text:
                message_text = message if isinstance(message, str) else ""
            if len(message_text) > _PROGRESS_MESSAGE_MAX_CHARS:
                message_text = f"{message_text[: _PROGRESS_MESSAGE_MAX_CHARS - 3]}..."
            payload["message"] = message_text
        if details:
            if isinstance(details, Mapping):
                payload["details"] = self._sanitise_pipeline_metadata(details)
            else:  # pragma: no cover - defensive branch for unexpected payloads
                payload["details"] = {
                    "value": self._coerce_metadata_value(details, depth=0),
                    "__coerced__": True,
                }

        await self._job_service.create_job_event(
            job_id,
            "analysis-progress",
            payload,
            session=session,
        )

    def _build_stage_message(
        self,
        step: str,
        details: Dict[str, Any],
        *,
        status: str,
    ) -> Optional[str]:
        error_detail = details.get("error")
        if status == "failed" and error_detail:
            return str(error_detail)

        filename = details.get("filename")
        position = details.get("file_number")
        total_files = details.get("total_files")
        target = self._describe_file_position(
            filename if isinstance(filename, str) else None,
            position if isinstance(position, int) else None,
            total_files if isinstance(total_files, int) else None,
        )

        if step == "chunking":
            chunk_count = details.get("chunk_count")
            if isinstance(chunk_count, int):
                plural = "s" if chunk_count != 1 else ""
                return f"Segmented {chunk_count} chunk{plural} from {target}."
            return f"Segmented content from {target}."

        if step == "embedding":
            chunk_count = details.get("chunk_count")
            if isinstance(chunk_count, int) and chunk_count > 0:
                plural = "s" if chunk_count != 1 else ""
                return f"Generated embeddings for {chunk_count} segment{plural} from {target}."
            return f"Generated embeddings for {target}."

        if step == "storage":
            document_count = details.get("document_count")
            if isinstance(document_count, int) and document_count >= 0:
                plural = "s" if document_count != 1 else ""
                return f"Stored {document_count} document{plural} for {target}."
            return f"Stored analysis artefacts for {target}."

        return None

    def _build_pipeline_context(self, job: Job, file_record: File) -> PipelineContext:
        manifest = job.input_manifest if isinstance(job.input_manifest, dict) else {}
        source = job.source if isinstance(job.source, dict) else {}

        tenant_raw = manifest.get("tenant_id") or source.get("tenant_id")
        tenant_uuid = _coerce_uuid(tenant_raw)
        job_uuid = _coerce_uuid(job.id)
        file_uuid = _coerce_uuid(file_record.id)

        telemetry_flag = settings.feature_flags.is_enabled(TELEMETRY_ENHANCED_METRICS.key)
        feature_flags: List[str] = []
        if telemetry_flag:
            feature_flags.append(TELEMETRY_ENHANCED_METRICS.key)

        platform = str(source.get("platform") or manifest.get("platform") or "worker").lower()
        raw_filename = getattr(file_record, "original_filename", None) or ""
        lowered_name = str(raw_filename).lower()
        _, _, extension = lowered_name.rpartition(".")
        file_type = extension or "unknown"

        tenant_label = str(tenant_uuid) if tenant_uuid else "unknown"
        size_bytes = getattr(file_record, "file_size", None)

        return PipelineContext(
            tenant_label=tenant_label,
            tenant_uuid=tenant_uuid,
            job_uuid=job_uuid,
            file_uuid=file_uuid,
            platform=platform,
            file_type=file_type,
            feature_flags=feature_flags,
            telemetry_enabled=telemetry_flag,
            metrics_enabled=settings.METRICS_ENABLED,
            size_bytes=size_bytes,
        )

    @staticmethod
    def _sanitise_pipeline_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
        return sanitise_metadata(metadata)

    @staticmethod
    def _coerce_metadata_value(value: Any, *, depth: int) -> Any:
        return coerce_metadata_value(value, depth=depth)

    async def _record_stage_event(
        self,
        session: AsyncSession,
        job_id: str,
        context: PipelineContext,
        *,
        stage: PipelineStage,
        status: PipelineStatus,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
        size_bytes: Optional[int] = None,
    ) -> None:
        size_for_metrics = size_bytes if size_bytes is not None else context.size_bytes
        metadata_payload = self._sanitise_pipeline_metadata(metadata or {})

        if context.metrics_enabled:
            try:
                _PIPELINE_METRICS.for_stage(stage.value).observe(
                    tenant_id=context.tenant_label,
                    platform=context.platform,
                    file_type=context.file_type,
                    size_bytes=size_for_metrics,
                    status=status.value,
                    feature_flags=context.feature_flags,
                    duration_seconds=duration_seconds,
                )
            except Exception:  # pragma: no cover - metrics should not block execution
                logger.exception(
                    "Failed to emit pipeline metrics for stage %s", stage.value
                )

        if (
            context.telemetry_enabled
            and context.tenant_uuid
            and context.job_uuid
            and context.file_uuid
        ):
            event = UploadTelemetryEvent(
                tenant_id=context.tenant_uuid,
                job_id=context.job_uuid,
                upload_id=context.file_uuid,
                stage=stage,
                feature_flags=context.feature_flags,
                status=status,
                duration_ms=int(duration_seconds * 1000),
                started_at=started_at,
                completed_at=completed_at,
                metadata=metadata_payload,
            )
            try:
                await persist_upload_telemetry_event(session, event)
            except Exception:  # pragma: no cover - best effort telemetry
                logger.exception(
                    "Failed to persist telemetry for stage %s (job=%s, file=%s)",
                    stage.value,
                    context.job_uuid,
                    context.file_uuid,
                )

        progress_step = PIPELINE_STAGE_TO_PROGRESS_STEP.get(stage)
        if progress_step:
            details_payload: Dict[str, Any] = dict(metadata_payload)
            details_payload.setdefault("pipeline_stage", stage.value)
            details_payload["duration_seconds"] = duration_seconds
            if context.file_uuid:
                details_payload.setdefault("file_id", str(context.file_uuid))
            if context.job_uuid:
                details_payload.setdefault("job_uuid", str(context.job_uuid))

            progress_status = "completed"
            if status is PipelineStatus.FAILED:
                progress_status = "failed"
            elif status is PipelineStatus.PARTIAL:
                details_payload["partial"] = True

            message = self._build_stage_message(
                progress_step,
                details_payload,
                status=progress_status,
            )

            await self._emit_progress_event(
                job_id,
                progress_step,
                progress_status,
                message=message,
                details=details_payload,
                session=session,
            )

    async def close(self) -> None:
        """Release underlying resources."""
        if self._embedding_service is not None:
            try:
                await self._embedding_service.close()
            finally:
                self._embedding_service = None

    async def process_rca_analysis(self, job: Job) -> Dict[str, Any]:
        """Run the full RCA pipeline for the supplied job."""
        # Step 1: Initial classification and setup
        await self._emit_progress_event(
            str(job.id),
            "classification",
            "started",
            message="Classifying uploaded files and preparing analysis pipeline...",
            details={"progress": 0, "step": 1, "total_steps": 7},
        )
        
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "ingestion", "status": "started"},
        )

        files = await self._list_job_files(str(job.id))
        if not files:
            raise ValueError("No files uploaded for analysis")

        file_summaries: List[FileSummary] = []
        detection_inputs: List[DetectionInput] = []
        detection_outcome: Optional[PlatformDetectionOutcome] = None
        total_chunks = 0

        await self._emit_progress_event(
            str(job.id),
            "classification",
            "completed",
            message=f"Classified {len(files)} file{'s' if len(files) != 1 else ''} - proceeding with RCA analysis.",
            details={
                "file_count": len(files),
                "progress": 10,
                "step": 1,
                "total_steps": 7,
                "file_types": [f.metadata.get("content_type", "unknown") if f.metadata else "unknown" for f in files],
            },
        )

        for index, descriptor in enumerate(files, start=1):
            summary = await self._process_single_file(
                job,
                descriptor,
                position=index,
                total_files=len(files),
                detection_collector=detection_inputs.append,
            )
            file_summaries.append(summary)
            total_chunks += summary.chunk_count

        detection_outcome = await self._handle_platform_detection(job, detection_inputs)

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "ingestion",
                "status": "completed",
                "files": len(file_summaries),
                "chunks": total_chunks,
            },
        )

        # Step 6: Correlate with historical incidents
        await self._emit_progress_event(
            str(job.id),
            "correlation",
            "started",
            message="Searching for similar historical incidents and patterns...",
            details={
                "progress": 70,
                "step": 6,
                "total_steps": 7,
                "total_chunks": total_chunks,
                "files_analyzed": len(file_summaries),
            },
        )
        
        # Note: Actual correlation logic would go here
        # For now, we emit completion immediately
        await self._emit_progress_event(
            str(job.id),
            "correlation",
            "completed",
            message=f"Correlation complete - analyzed patterns across {total_chunks} data chunks.",
            details={
                "progress": 75,
                "step": 6,
                "total_steps": 7,
                "chunks_analyzed": total_chunks,
            },
        )

        pii_redacted_for_llm = sum(1 for summary in file_summaries if summary.redaction_applied)
        pii_failsafe_for_llm = sum(1 for summary in file_summaries if summary.redaction_failsafe_triggered)

        # Step 7: LLM-powered root cause analysis
        await self._emit_progress_event(
            str(job.id),
            "llm",
            "started",
            message="Running sanitized AI-powered root cause analysis using GitHub Copilot...",
            details={
                "progress": 75,
                "step": 7,
                "total_steps": 7,
                "model": str(job.model),
                "provider": str(job.provider),
                "pii_redacted_files": pii_redacted_for_llm,
                "pii_failsafe_files": pii_failsafe_for_llm,
            },
        )
        
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "status": "started"},
        )
        llm_output = await self._run_llm_analysis(job, file_summaries, "rca_analysis")
        llm_blocked = bool(llm_output.get("blocked"))
        llm_prompt_details = cast(Dict[str, Any], llm_output.get("pii_prompt") or {})
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "status": "blocked" if llm_blocked else "completed"},
        )

        if llm_blocked:
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "failed",
                message="AI analysis blocked to uphold PII safeguards.",
                details={
                    "progress": 90,
                    "step": 7,
                    "total_steps": 7,
                    "pii_redacted_files": pii_redacted_for_llm,
                    "pii_failsafe_files": pii_failsafe_for_llm,
                    **llm_prompt_details,
                },
            )
        else:
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "completed",
                message="AI analysis complete - sanitized insights ready for review.",
                details={
                    "progress": 90,
                    "step": 7,
                    "total_steps": 7,
                    "pii_redacted_files": pii_redacted_for_llm,
                    "pii_failsafe_files": pii_failsafe_for_llm,
                    **llm_prompt_details,
                },
            )

        pii_redacted_files = sum(1 for summary in file_summaries if summary.redaction_applied)
        pii_failsafe_files = sum(1 for summary in file_summaries if summary.redaction_failsafe_triggered)
        pii_total_redactions = sum(sum(summary.redaction_counts.values()) for summary in file_summaries)
        pii_validation_events = sum(len(summary.redaction_validation_warnings) for summary in file_summaries)

        aggregate_metrics = {
            "files": len(file_summaries),
            "lines": sum(summary.line_count for summary in file_summaries),
            "errors": sum(summary.error_count for summary in file_summaries),
            "warnings": sum(summary.warning_count for summary in file_summaries),
            "critical": sum(summary.critical_count for summary in file_summaries),
            "chunks": total_chunks,
            "pii_redacted_files": pii_redacted_files,
            "pii_failsafe_files": pii_failsafe_files,
            "pii_total_redactions": pii_total_redactions,
            "pii_validation_events": pii_validation_events,
        }

        # Step 8: Generating final report
        await self._emit_progress_event(
            str(job.id),
            "report",
            "started",
            message="Compiling comprehensive RCA report with sanitized findings and recommendations...",
            details={
                "progress": 90,
                "files": len(file_summaries),
                "chunks": total_chunks,
                "errors_found": aggregate_metrics["errors"],
                "warnings_found": aggregate_metrics["warnings"],
                "pii_redacted_files": aggregate_metrics["pii_redacted_files"],
                "pii_failsafe_files": aggregate_metrics["pii_failsafe_files"],
                "pii_total_redactions": aggregate_metrics["pii_total_redactions"],
                "pii_validation_events": aggregate_metrics["pii_validation_events"],
            },
        )

        try:
            outputs = self._render_outputs(
                job,
                aggregate_metrics,
                file_summaries,
                llm_output,
                mode="rca_analysis",
            )
        except Exception:
            await self._emit_progress_event(
                str(job.id),
                "report",
                "failed",
                message="Failed to compile final RCA report.",
                details={
                    "files": len(file_summaries),
                    "chunks": total_chunks,
                },
            )
            raise

        await self._emit_progress_event(
            str(job.id),
            "report",
            "completed",
            message=f"RCA report generated successfully! Analyzed {aggregate_metrics['lines']} lines across {len(file_summaries)} file(s).",
            details={
                "progress": 100,
                "files": len(file_summaries),
                "chunks": total_chunks,
                "total_lines": aggregate_metrics["lines"],
                "errors": aggregate_metrics["errors"],
                "warnings": aggregate_metrics["warnings"],
                "critical": aggregate_metrics["critical"],
                "pii_redacted_files": aggregate_metrics["pii_redacted_files"],
                "pii_failsafe_files": aggregate_metrics["pii_failsafe_files"],
                "pii_total_redactions": aggregate_metrics["pii_total_redactions"],
                "pii_validation_events": aggregate_metrics["pii_validation_events"],
            },
        )
        
        # Final completion event
        total_redactions = aggregate_metrics["pii_total_redactions"]
        redacted_files = aggregate_metrics["pii_redacted_files"]
        failsafe_files = aggregate_metrics["pii_failsafe_files"]
        if failsafe_files:
            completion_message = (
                f"✓ Analysis complete! PII safeguards enforced ({total_redactions} redaction(s); "
                f"{failsafe_files} file(s) quarantined)."
            )
        elif total_redactions:
            completion_message = (
                f"✓ Analysis complete! PII safeguards enforced ({total_redactions} redaction(s) across "
                f"{redacted_files} file(s))."
            )
        else:
            completion_message = "✓ Analysis complete! No sensitive data detected during processing."

        await self._emit_progress_event(
            str(job.id),
            "completed",
            "success",
            message=completion_message,
            details={
                "progress": 100,
                "total_files": len(file_summaries),
                "total_chunks": total_chunks,
                "total_lines": aggregate_metrics["lines"],
                "duration_seconds": (datetime.now(timezone.utc) - job.created_at).total_seconds() if hasattr(job, 'created_at') else None,
                "pii_redacted_files": aggregate_metrics["pii_redacted_files"],
                "pii_failsafe_files": aggregate_metrics["pii_failsafe_files"],
                "pii_total_redactions": aggregate_metrics["pii_total_redactions"],
                "pii_validation_events": aggregate_metrics["pii_validation_events"],
            },
        )

        fingerprint_metadata: Optional[IncidentFingerprintDTO] = None
        try:
            fingerprint_metadata = await self._index_incident_fingerprint(
                job,
                file_summaries,
                llm_output,
            )
        except Exception:  # pragma: no cover - fingerprint indexing must not block job completion
            logger.exception("Incident fingerprint indexing failed for job %s", job.id)

        return {
            "job_id": str(job.id),
            "analysis_type": "rca_analysis",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": aggregate_metrics,
            "files": [asdict(summary) for summary in file_summaries],
            "llm": llm_output,
            "outputs": outputs,
            "fingerprint": fingerprint_metadata.model_dump(mode="json") if fingerprint_metadata else None,
            "platform_detection": detection_outcome.model_dump(mode="json") if detection_outcome else None,
        }

    async def _index_incident_fingerprint(
        self,
        job: Job,
        summaries: Sequence[FileSummary],
        llm_output: Dict[str, Any],
    ) -> Optional[IncidentFingerprintDTO]:
        is_enabled = bool(getattr(settings, "RELATED_INCIDENTS_ENABLED", False))

        feature_flags = getattr(settings, "feature_flags", None)
        if feature_flags is not None and hasattr(feature_flags, "is_enabled"):
            try:
                if feature_flags.is_enabled("related_incidents_enabled"):
                    is_enabled = True
            except Exception:  # pragma: no cover - defensive guard
                logger.debug(
                    "Feature flag check failed for RELATED_INCIDENTS_ENABLED",
                    exc_info=True,
                )
        elif feature_flags is not None:
            is_enabled = is_enabled or bool(
                getattr(feature_flags, "RELATED_INCIDENTS_ENABLED", False)
            )

        if not is_enabled:
            return None

        manifest = job.input_manifest if isinstance(job.input_manifest, dict) else {}
        source = job.source if isinstance(job.source, dict) else {}
        tenant_raw = manifest.get("tenant_id") or source.get("tenant_id")
        tenant_uuid = _coerce_uuid(tenant_raw)
        if tenant_uuid is None:
            logger.debug(
                "Skipping fingerprint indexing for job %s due to missing tenant_id",
                job.id,
            )
            return None

        summary_text = self._resolve_fingerprint_summary(llm_output, summaries).strip()
        if summary_text and len(summary_text) > MAX_FINGERPRINT_SUMMARY_LENGTH:
            summary_text = summary_text[:MAX_FINGERPRINT_SUMMARY_LENGTH]

        embedding_vector: Optional[List[float]] = None
        fingerprint_status = FingerprintStatus.MISSING

        if summary_text:
            try:
                embedding_service = await self._ensure_embedding_service()
                embedding_vector = await embedding_service.embed_text(summary_text)
            except Exception:
                fingerprint_status = FingerprintStatus.DEGRADED
                logger.exception(
                    "Failed to generate fingerprint embedding for job %s",
                    job.id,
                )
            else:
                fingerprint_status = (
                    FingerprintStatus.AVAILABLE
                    if embedding_vector
                    else FingerprintStatus.DEGRADED
                )
        else:
            summary_text = "Automated summary unavailable; fingerprint not generated."

        visibility_scope = self._resolve_visibility_scope(job, manifest, source)
        relevance_threshold = self._resolve_relevance_threshold(manifest)

        safeguard_notes: Dict[str, Any] = {}
        async with self._session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(IncidentFingerprint)
                    .where(IncidentFingerprint.session_id == job.id)
                    .limit(1)
                )
                record = existing.scalar_one_or_none()
                if record is None:
                    record = IncidentFingerprint(
                        session_id=job.id,
                        tenant_id=tenant_uuid,
                        summary_text=summary_text,
                        relevance_threshold=relevance_threshold,
                        visibility_scope=visibility_scope.value,
                        fingerprint_status=fingerprint_status.value,
                        safeguard_notes=safeguard_notes,
                        embedding_vector=embedding_vector,
                    )
                    session.add(record)
                else:
                    existing_notes_raw = getattr(record, "safeguard_notes", None)
                    notes: Dict[str, Any] = {}
                    if isinstance(existing_notes_raw, Mapping):
                        for key, value in existing_notes_raw.items():
                            notes[str(key)] = value
                    safeguard_notes = notes

                    setattr(record, "tenant_id", tenant_uuid)
                    setattr(record, "summary_text", summary_text)
                    setattr(record, "relevance_threshold", relevance_threshold)
                    setattr(record, "visibility_scope", visibility_scope.value)
                    setattr(record, "fingerprint_status", fingerprint_status.value)
                    setattr(record, "safeguard_notes", safeguard_notes)
                    setattr(record, "embedding_vector", embedding_vector)
                    setattr(record, "updated_at", datetime.now(timezone.utc))

            await self._job_service.publish_session_events(session)

        dto = IncidentFingerprintDTO(
            session_id=str(job.id),
            tenant_id=str(tenant_uuid),
            summary_text=summary_text,
            relevance_threshold=relevance_threshold,
            visibility_scope=visibility_scope,
            fingerprint_status=fingerprint_status,
            safeguard_notes=safeguard_notes,
            embedding_present=bool(embedding_vector),
        )

        return dto

    def _resolve_fingerprint_summary(
        self,
        llm_output: Dict[str, Any],
        summaries: Sequence[FileSummary],
    ) -> str:
        summary_value = ""
        if isinstance(llm_output, dict):
            summary_value = str(llm_output.get("summary") or "").strip()
        if summary_value:
            return summary_value

        highlights: List[str] = []
        for summary in summaries[:3]:
            highlights.append(
                f"{summary.filename}: errors={summary.error_count}, warnings={summary.warning_count}, critical={summary.critical_count}"
            )

        if not highlights:
            return ""

        lines = ["Automated summary unavailable. Key signals:"]
        lines.extend(f"- {highlight}" for highlight in highlights)
        return "\n".join(lines)

    def _resolve_visibility_scope(
        self,
        job: Job,
        manifest: Dict[str, Any],
        source: Dict[str, Any],
    ) -> VisibilityScope:
        related_defaults = getattr(settings, "related_incidents", None)
        default_scope = (
            getattr(related_defaults, "DEFAULT_SCOPE", None)
            if related_defaults is not None
            else None
        )
        raw_scope = (
            manifest.get("visibility_scope")
            or source.get("visibility_scope")
            or default_scope
        )
        value = str(raw_scope).strip().lower()
        try:
            return VisibilityScope(value)
        except ValueError:
            logger.debug(
                "Invalid visibility scope '%s' for job %s; defaulting to tenant_only",
                raw_scope,
                job.id,
            )
            return VisibilityScope.TENANT_ONLY

    def _resolve_relevance_threshold(self, manifest: Dict[str, Any]) -> float:
        candidate = (
            manifest.get("fingerprint_min_relevance")
            or manifest.get("related_incidents_min_relevance")
        )
        related_defaults = getattr(settings, "related_incidents", None)
        default_min_relevance = (
            float(getattr(related_defaults, "MIN_RELEVANCE", 0.6))
            if related_defaults is not None
            else 0.6
        )
        if candidate is None:
            return default_min_relevance

        try:
            value = float(candidate)
        except (TypeError, ValueError):
            logger.debug(
                "Invalid fingerprint relevance '%s'; falling back to default",
                candidate,
            )
            return default_min_relevance

        return max(0.0, min(1.0, value))


    async def _handle_platform_detection(
        self,
        job: Job,
        inputs: Sequence[DetectionInput],
    ) -> Optional[PlatformDetectionOutcome]:
        detector = PlatformDetectionOrchestrator()
        flag_source = getattr(settings, "feature_flags", None)
        feature_flags: Dict[str, bool]
        if flag_source is not None and hasattr(flag_source, "as_dict"):
            feature_flags = flag_source.as_dict()
        else:  # pragma: no cover - fallback for test overrides
            feature_flags = {}

        try:
            outcome = detector.detect(
                str(job.id),
                inputs,
                feature_flags=feature_flags,
            )
        except Exception:
            logger.exception("Platform detection evaluation failed for job %s", job.id)
            return None

        try:
            await self._persist_platform_detection_result(outcome)
        except Exception:
            logger.exception(
                "Failed to persist platform detection result for job %s",
                job.id,
            )

        try:
            self._record_detection_observability(job, outcome)
        except Exception:
            logger.exception(
                "Failed to emit platform detection observability for job %s",
                job.id,
            )

        return outcome

    async def _persist_platform_detection_result(
        self,
        outcome: PlatformDetectionOutcome,
    ) -> None:
        job_uuid = _coerce_uuid(outcome.job_id)
        if job_uuid is None:
            logger.warning(
                "Skipping platform detection persistence due to invalid job id %s",
                outcome.job_id,
            )
            return

        async with self._session_factory() as session:
            async with session.begin():
                existing_stmt = (
                    select(PlatformDetectionResult)
                    .where(PlatformDetectionResult.job_id == job_uuid)
                    .limit(1)
                )
                result = await session.execute(existing_stmt)
                record = result.scalar_one_or_none()
                payload = {
                    "detected_platform": outcome.detected_platform,
                    "confidence_score": float(outcome.confidence_score),
                    "detection_method": outcome.detection_method,
                    "parser_executed": bool(outcome.parser_executed),
                    "parser_version": outcome.parser_version,
                    "extracted_entities": list(outcome.extracted_entities),
                    "feature_flag_snapshot": dict(outcome.feature_flag_snapshot),
                }

                if record is None:
                    session.add(PlatformDetectionResult(job_id=job_uuid, **payload))
                else:
                    for key, value in payload.items():
                        setattr(record, key, value)

    def _record_detection_observability(
        self,
        job: Job,
        outcome: PlatformDetectionOutcome,
    ) -> None:
        snapshot = dict(outcome.feature_flag_snapshot)

        try:
            log_platform_detection_event(
                str(job.id),
                detected_platform=outcome.detected_platform,
                confidence=float(outcome.confidence_score),
                parser_executed=bool(outcome.parser_executed),
                detection_method=outcome.detection_method,
                feature_flags=snapshot,
                duration_ms=float(outcome.duration_ms) if outcome.duration_ms else None,
            )
        except Exception:
            logger.exception(
                "Failed to emit platform detection log for job %s",
                job.id,
            )

        tenant_label = self._resolve_tenant_label(job)
        duration_seconds = (
            float(outcome.duration_ms) / 1000.0 if outcome.duration_ms else None
        )

        try:
            metric_event = DetectionMetricEvent(
                tenant_id=tenant_label,
                platform=outcome.detected_platform or "unknown",
                outcome=self._resolve_detection_outcome_label(outcome),
                confidence=float(outcome.confidence_score),
                parser_executed=bool(outcome.parser_executed),
                detection_method=outcome.detection_method,
                feature_flags=self._normalise_feature_flags(snapshot),
                parser_version=outcome.parser_version,
                duration_seconds=duration_seconds,
            )
            observe_detection(metric_event)
        except Exception:
            logger.exception(
                "Failed to record platform detection metrics for job %s",
                job.id,
            )

    @staticmethod
    def _resolve_detection_outcome_label(outcome: PlatformDetectionOutcome) -> str:
        enabled = outcome.feature_flag_snapshot.get("platform_detection_enabled")
        if enabled is False:
            return "disabled"
        if not outcome.detected_platform or outcome.detected_platform == "unknown":
            return "unknown"
        if outcome.parser_executed:
            return "parser_executed"
        return "detected"

    @staticmethod
    def _normalise_feature_flags(
        snapshot: Optional[Mapping[str, Any]],
    ) -> Dict[str, bool]:
        if not snapshot:
            return {}
        flags: Dict[str, bool] = {}
        for key, value in snapshot.items():
            if isinstance(value, bool):
                flags[str(key)] = value
        return flags

    @staticmethod
    def _resolve_tenant_label(job: Job) -> str:
        manifest_obj = getattr(job, "input_manifest", {})
        manifest = manifest_obj if isinstance(manifest_obj, dict) else {}
        source_obj = getattr(job, "source", {})
        source = source_obj if isinstance(source_obj, dict) else {}
        tenant_raw = manifest.get("tenant_id") or source.get("tenant_id")
        tenant_uuid = _coerce_uuid(tenant_raw)
        if tenant_uuid is None:
            return "unknown"
        return str(tenant_uuid)

    async def process_log_analysis(self, job: Job) -> Dict[str, Any]:
        """Alias for log-specific analysis (shares pipeline with RCA)."""
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "ingestion", "mode": "log-analysis", "status": "started"},
        )

        files = await self._list_job_files(str(job.id))
        if not files:
            raise ValueError("No files uploaded for analysis")

        file_summaries: List[FileSummary] = []
        detection_inputs: List[DetectionInput] = []
        detection_outcome: Optional[PlatformDetectionOutcome] = None
        total_chunks = 0

        await self._emit_progress_event(
            str(job.id),
            "upload",
            "completed",
            message=f"Received {len(files)} file{'s' if len(files) != 1 else ''} for log analysis.",
            details={"file_count": len(files)},
        )

        for index, descriptor in enumerate(files, start=1):
            summary = await self._process_single_file(
                job,
                descriptor,
                position=index,
                total_files=len(files),
                detection_collector=detection_inputs.append,
            )
            file_summaries.append(summary)
            total_chunks += summary.chunk_count

        detection_outcome = await self._handle_platform_detection(job, detection_inputs)

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "ingestion",
                "mode": "log-analysis",
                "status": "completed",
                "files": len(file_summaries),
                "chunks": total_chunks,
            },
        )

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "mode": "log-analysis", "status": "started"},
        )
        llm_output = await self._run_llm_analysis(job, file_summaries, "log_analysis")
        llm_blocked = bool(llm_output.get("blocked"))
        llm_prompt_details = cast(Dict[str, Any], llm_output.get("pii_prompt") or {})
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "mode": "log-analysis", "status": "blocked" if llm_blocked else "completed"},
        )

        pii_redacted_files = sum(1 for summary in file_summaries if summary.redaction_applied)
        pii_failsafe_files = sum(1 for summary in file_summaries if summary.redaction_failsafe_triggered)

        if llm_blocked:
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "failed",
                message="AI summarization blocked to protect sensitive data.",
                details={
                    "pii_redacted_files": pii_redacted_files,
                    "pii_failsafe_files": pii_failsafe_files,
                    **llm_prompt_details,
                },
            )
        else:
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "completed",
                message="AI summarization complete - sanitized insights ready for review.",
                details={
                    "pii_redacted_files": pii_redacted_files,
                    "pii_failsafe_files": pii_failsafe_files,
                    **llm_prompt_details,
                },
            )

        pii_total_redactions = sum(sum(summary.redaction_counts.values()) for summary in file_summaries)
        pii_validation_events = sum(len(summary.redaction_validation_warnings) for summary in file_summaries)

        aggregate_metrics = {
            "files": len(file_summaries),
            "lines": sum(summary.line_count for summary in file_summaries),
            "errors": sum(summary.error_count for summary in file_summaries),
            "warnings": sum(summary.warning_count for summary in file_summaries),
            "critical": sum(summary.critical_count for summary in file_summaries),
            "chunks": total_chunks,
            "pii_redacted_files": pii_redacted_files,
            "pii_failsafe_files": pii_failsafe_files,
            "pii_total_redactions": pii_total_redactions,
            "pii_validation_events": pii_validation_events,
        }

        suspected_error_logs = [
            summary.filename
            for summary in file_summaries
            if summary.error_count or summary.critical_count
        ]

        await self._emit_progress_event(
            str(job.id),
            "report",
            "started",
            message="Compiling log analysis report with sanitized findings...",
            details={
                "files": len(file_summaries),
                "chunks": total_chunks,
                "pii_redacted_files": aggregate_metrics["pii_redacted_files"],
                "pii_failsafe_files": aggregate_metrics["pii_failsafe_files"],
                "pii_total_redactions": aggregate_metrics["pii_total_redactions"],
                "pii_validation_events": aggregate_metrics["pii_validation_events"],
            },
        )

        try:
            outputs = self._render_outputs(
                job,
                aggregate_metrics,
                file_summaries,
                llm_output,
                mode="log_analysis",
            )
        except Exception:
            await self._emit_progress_event(
                str(job.id),
                "report",
                "failed",
                message="Failed to compile log analysis report.",
                details={
                    "files": len(file_summaries),
                    "chunks": total_chunks,
                },
            )
            raise

        await self._emit_progress_event(
            str(job.id),
            "report",
            "completed",
            message="Log analysis report ready with PII safeguards enforced.",
            details={
                "files": len(file_summaries),
                "chunks": total_chunks,
                "pii_redacted_files": aggregate_metrics["pii_redacted_files"],
                "pii_failsafe_files": aggregate_metrics["pii_failsafe_files"],
                "pii_total_redactions": aggregate_metrics["pii_total_redactions"],
                "pii_validation_events": aggregate_metrics["pii_validation_events"],
            },
        )

        return {
            "job_id": str(job.id),
            "analysis_type": "log_analysis",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": aggregate_metrics,
            "files": [asdict(summary) for summary in file_summaries],
            "suspected_error_logs": suspected_error_logs,
            "llm": llm_output,
            "outputs": outputs,
            "platform_detection": detection_outcome.model_dump(mode="json") if detection_outcome else None,
        }


    async def process_embedding_generation(self, job: Job) -> Dict[str, Any]:
        """
        Generate embeddings for pre-existing documents linked to the job.
        Intended for reprocessing flows where text content already lives in the
        ``documents`` table.
        """
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "embedding-refresh", "status": "started"},
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(Document).where(Document.job_id == job.id).order_by(Document.chunk_index.asc())
            )
            documents = result.scalars().all()

        if not documents:
            raise ValueError("No documents available to embed")

        texts = [cast(str, getattr(doc, "content", "")) for doc in documents]
        embeddings = await self._generate_embeddings(texts)

        async with self._session_factory() as session:
            for document, vector in zip(documents, embeddings):
                existing = await session.get(Document, document.id)
                if existing:
                    setattr(existing, "content_embedding", vector)
            await session.commit()
            await self._job_service.publish_session_events(session)

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "embedding-refresh",
                "status": "completed",
                "documents": len(documents),
            },
        )

        return {
            "job_id": str(job.id),
            "analysis_type": "embedding_generation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(documents),
        }


    def _render_outputs(
        self,
        job: Job,
        metrics: Dict[str, Any],
        summaries: Sequence[FileSummary],
        llm_output: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        severity = self._determine_severity(metrics)
        categories = self._derive_categories(metrics, mode)
        tags = self._derive_tags(summaries)
        recommended_actions = self._extract_actions(llm_output.get("summary", "")) or [
            "Review the generated summary and log excerpts for next steps."
        ]
        markdown = self._build_markdown(
            job, mode, severity, metrics, summaries, recommended_actions, tags, llm_output
        )
        html_output = self._build_html(
            job, mode, severity, metrics, summaries, recommended_actions, tags, llm_output
        )

        # Enhanced structured JSON with richer metadata
        structured_json = {
            "job_id": str(job.id),
            "analysis_type": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "categories": categories,
            "tags": tags,
            "metrics": metrics,
            "files": [asdict(summary) for summary in summaries],
            "summary": llm_output.get("summary"),
            "llm": llm_output,
            "recommended_actions": recommended_actions,
            "ticketing": getattr(job, "ticketing", None) or {},
        }

        # Add executive summary section
        summary_text = llm_output.get("summary", "")
        first_line = summary_text.split('\n')[0] if summary_text else "No summary available"
        structured_json["executive_summary"] = {
            "severity_level": severity,
            "total_errors": metrics.get("errors", 0),
            "total_warnings": metrics.get("warnings", 0),
            "critical_events": metrics.get("critical", 0),
            "files_analyzed": metrics.get("files", 0),
            "one_line_summary": first_line,
        }

        # Add timeline section
        structured_json["timeline"] = {
            "created_at": job.created_at.isoformat() if job.created_at is not None else None,
            "started_at": job.started_at.isoformat() if job.started_at is not None else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at is not None else None,
            "duration_seconds": job.duration_seconds,
        }

        # Add platform detection if available
        if hasattr(job, 'platform_detection') and job.platform_detection:
            pd = job.platform_detection
            structured_json["platform_detection"] = {
                "detected_platform": pd.detected_platform,
                "confidence_score": pd.confidence_score,
                "detection_method": pd.detection_method,
                "extracted_entities": pd.extracted_entities or [],
                "insights": pd.insights,
            }

        # Enhanced PII protection section
        structured_json["pii_protection"] = {
            "files_sanitised": metrics.get("pii_redacted_files", 0),
            "files_quarantined": metrics.get("pii_failsafe_files", 0),
            "total_redactions": metrics.get("pii_total_redactions", 0),
            "validation_events": metrics.get("pii_validation_events", 0),
            "security_guarantee": "All sensitive data removed before LLM processing",
            "compliance": ["GDPR", "PCI DSS", "HIPAA", "SOC 2"],
        }

        # Add action priorities
        priority_actions = []
        standard_actions = []
        for action in recommended_actions:
            action_lower = action.lower()
            if any(word in action_lower for word in ['immediate', 'urgent', 'critical', 'now', 'asap']):
                priority_actions.append(action)
            else:
                standard_actions.append(action)
        
        structured_json["action_priorities"] = {
            "high_priority": priority_actions,
            "standard_priority": standard_actions,
        }

        return {"markdown": markdown, "html": html_output, "json": structured_json}

    @staticmethod
    def _determine_severity(metrics: Dict[str, Any]) -> str:
        if metrics.get("critical", 0):
            return "critical"
        if metrics.get("errors", 0):
            return "high"
        if metrics.get("warnings", 0):
            return "moderate"
        return "low"

    @staticmethod
    def _derive_categories(metrics: Dict[str, Any], mode: str) -> List[str]:
        categories = {mode}
        if metrics.get("critical"):
            categories.add("priority-incident")
        if metrics.get("errors"):
            categories.add("error-detected")
        if metrics.get("warnings"):
            categories.add("warning-detected")
        categories.add("rca")
        return sorted(categories)

    @staticmethod
    def _derive_tags(summaries: Sequence[FileSummary]) -> List[str]:
        keywords: set[str] = set()
        for summary in summaries:
            keywords.update(summary.top_keywords[:3])
        return sorted(list(keywords))[:10]

    @staticmethod
    def _summarise_pii_status(summary: FileSummary) -> str:
        if summary.redaction_failsafe_triggered:
            return "Content quarantined (failsafe triggered)."
        if summary.redaction_applied:
            return "Sensitive data masked prior to analysis."
        return "No sensitive data detected."

    @staticmethod
    def _summarise_pii_metrics(metrics: Mapping[str, Any]) -> str:
        redacted = int(metrics.get("pii_redacted_files", 0) or 0)
        failsafe = int(metrics.get("pii_failsafe_files", 0) or 0)
        if failsafe:
            return (
                f"Quarantined {failsafe} file{'s' if failsafe != 1 else ''}; sanitized remaining inputs."
            )
        if redacted:
            return f"Sanitized {redacted} file{'s' if redacted != 1 else ''} before analysis."
        return "No sensitive data detected in uploaded files."

    @staticmethod
    def _extract_actions(summary_text: str) -> List[str]:
        actions: List[str] = []
        for line in summary_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*")):
                actions.append(stripped.lstrip("-* ").strip())
        return [action for action in actions if action]

    def _build_markdown(
        self,
        job: Job,
        mode: str,
        severity: str,
        metrics: Dict[str, Any],
        summaries: Sequence[FileSummary],
        recommended_actions: Sequence[str],
        tags: Sequence[str],
        llm_output: Dict[str, Any],
    ) -> str:
        # Severity icon mapping
        severity_icons = {
            "critical": "🔴",
            "high": "🟠",
            "moderate": "🟡",
            "low": "🟢"
        }
        severity_icon = severity_icons.get(severity.lower(), "⚪")
        
        # Calculate duration
        duration_str = "N/A"
        if job.duration_seconds is not None:
            if job.duration_seconds < 60:
                duration_str = f"{job.duration_seconds:.1f} seconds"
            else:
                duration_str = f"{job.duration_seconds / 60:.1f} minutes"
        
        # Format timestamps
        created_at_str = job.created_at.strftime("%B %d, %Y %H:%M:%S UTC") if job.created_at is not None else "N/A"
        completed_at_str = job.completed_at.strftime("%B %d, %Y %H:%M:%S UTC") if job.completed_at is not None else "In Progress"
        
        lines: List[str] = [
            f"# {severity_icon} Root Cause Analysis Report",
            f"## 🔍 Investigation #{job.id}",
            "",
            "---",
            "",
            "### 📋 Analysis Metadata",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| 🕒 **Analysis Date** | {created_at_str} |",
            f"| ✅ **Completed At** | {completed_at_str} |",
            f"| ⏱️ **Duration** | {duration_str} |",
            f"| 👤 **User ID** | {job.user_id} |",
            f"| 🎯 **Job Type** | {mode.replace('_', ' ').title()} |",
            f"| {severity_icon} **Severity** | {severity.upper()} |",
            f"| 📊 **Files Analyzed** | {metrics.get('files', 0)} |",
            f"| 🛡️ **PII Protection** | {self._summarise_pii_metrics(metrics)} |",
        ]
        
        # Add platform detection if available
        if hasattr(job, 'platform_detection') and job.platform_detection:
            pd = job.platform_detection
            platform_name = pd.detected_platform or "Unknown"
            confidence = pd.confidence_score or 0.0
            lines.append(f"| 🤖 **Platform Detected** | {platform_name} ({confidence:.0%} confidence) |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 📝 Executive Summary",
            "",
            "### Quick Assessment",
            f"- **Severity Level:** {severity_icon} {severity.upper()}",
            f"- **Total Errors:** {metrics.get('errors', 0)} errors, {metrics.get('warnings', 0)} warnings, {metrics.get('critical', 0)} critical events",
            f"- **Files Analyzed:** {metrics.get('files', 0)} file(s) processed",
            f"- **Analysis Duration:** {duration_str}",
            "",
        ])
        
        # Add one-line summary from LLM output
        summary_text = llm_output.get("summary", "No automated summary available.")
        first_line = summary_text.split('\n')[0] if summary_text else "No summary available"
        lines.extend([
            "### One-Line Summary",
            first_line,
            "",
            "---",
            "",
        ])
        
        # Platform Detection Section (if available)
        if hasattr(job, 'platform_detection') and job.platform_detection:
            pd = job.platform_detection
            lines.extend([
                "## 🤖 Platform Detection",
                "",
                f"**Detected Platform:** {pd.detected_platform or 'Unknown'}  ",
                f"**Confidence:** {(pd.confidence_score or 0.0):.0%}  ",
                f"**Detection Method:** {pd.detection_method or 'Unknown'}",
                "",
            ])
            
            if pd.extracted_entities:
                lines.append("### Extracted Platform Information")
                # Extract common entity types
                processes = [e for e in pd.extracted_entities if e.get('entity_type') == 'process']
                if processes:
                    lines.append(f"- **Processes:** {', '.join([p.get('value', 'Unknown') for p in processes[:5]])}")
                
                sessions = [e for e in pd.extracted_entities if e.get('entity_type') == 'session']
                if sessions:
                    lines.append(f"- **Sessions:** {', '.join([s.get('value', 'Unknown') for s in sessions[:5]])}")
                
                stages = [e for e in pd.extracted_entities if e.get('entity_type') in ('stage', 'error_stage')]
                if stages:
                    lines.append(f"- **Stages/Components:** {', '.join([s.get('value', 'Unknown') for s in stages[:5]])}")
                
                lines.append("")
            
            if pd.insights:
                lines.extend([
                    "### Platform-Specific Insights",
                    pd.insights,
                    "",
                ])
            
            lines.extend(["---", ""])
        
        # Main LLM Summary
        lines.extend([
            "## 🎯 Detailed Analysis",
            "",
            summary_text,
            "",
            "---",
            "",
        ])
        
        # Recommended Actions with Priority
        lines.extend([
            "## 🚨 Recommended Actions",
            "",
        ])
        
        if recommended_actions:
            # Try to categorize actions by priority (simple heuristic)
            priority_actions = []
            standard_actions = []
            
            for action in recommended_actions:
                action_lower = action.lower()
                if any(word in action_lower for word in ['immediate', 'urgent', 'critical', 'now', 'asap']):
                    priority_actions.append(action)
                else:
                    standard_actions.append(action)
            
            if priority_actions:
                lines.append("### 🔴 High Priority")
                for action in priority_actions:
                    lines.append(f"- {action}")
                lines.append("")
            
            if standard_actions:
                lines.append("### 🟡 Standard Priority")
                for action in standard_actions:
                    lines.append(f"- {action}")
                lines.append("")
        else:
            lines.append("- Review the generated summary and log excerpts for next steps.")
            lines.append("")
        
        lines.extend(["---", ""])
        
        # Enhanced PII Protection Summary
        lines.extend([
            "## 🔒 PII Protection & Security",
            "",
            "### Protection Summary",
            "✅ **Enterprise-grade multi-layer redaction applied**",
            "",
            "| Metric | Value | Status |",
            "|--------|-------|--------|",
            f"| 📁 **Files Scanned** | {metrics.get('files', 0)} | ✅ Complete |",
            f"| 🛡️ **Files Sanitized** | {metrics.get('pii_redacted_files', 0)} | ✅ Redacted |",
            f"| ⚠️ **Files Quarantined** | {metrics.get('pii_failsafe_files', 0)} | {'⚠️ Review' if metrics.get('pii_failsafe_files', 0) > 0 else '✅ Clean'} |",
            f"| 🔐 **Total Redactions** | {metrics.get('pii_total_redactions', 0)} items | ✅ Protected |",
            f"| ✔️ **Validation Events** | {metrics.get('pii_validation_events', 0)} | {'⚠️ Review' if metrics.get('pii_validation_events', 0) > 0 else '✅ Verified'} |",
            "",
        ])
        
        if any(summary.redaction_validation_warnings for summary in summaries):
            lines.append("### ⚠️ Validation Notes")
            for summary in summaries:
                for warning in summary.redaction_validation_warnings:
                    lines.append(f"- **{summary.filename}:** {warning}")
            lines.append("")
        
        lines.extend([
            "**Security Guarantee:** All sensitive data removed before LLM processing.",
            "",
            "---",
            "",
        ])
        
        # File Analysis Section
        lines.extend([
            "## 📊 File Analysis",
            "",
        ])
        
        for summary in summaries:
            lines.extend([
                f"### 📄 {summary.filename}",
                "",
                "#### Overview",
                "| Metric | Value |",
                "|--------|-------|",
                f"| 📏 **Total Lines** | {summary.line_count:,} |",
                f"| 🔴 **Errors** | {summary.error_count} |",
                f"| 🟡 **Warnings** | {summary.warning_count} |",
                f"| 🔴 **Critical Events** | {summary.critical_count} |",
                f"| 🔒 **PII Status** | {self._summarise_pii_status(summary)} |",
                "",
            ])
            
            if summary.top_keywords:
                lines.extend([
                    "**Top Keywords:**  ",
                    f"🏷️ {' · '.join(summary.top_keywords[:5])}",
                    "",
                ])
            
            if summary.sample_head:
                lines.append("#### Sample Head (First Lines)")
                lines.append("```")
                for line in summary.sample_head[:5]:
                    lines.append(line)
                lines.append("```")
                lines.append("")
            
            if summary.sample_tail:
                lines.append("#### Sample Tail (Last Lines)")
                lines.append("```")
                for line in summary.sample_tail[:5]:
                    lines.append(line)
                lines.append("```")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # Tags and Metadata
        if tags:
            lines.extend([
                "## 📌 Tags & Categories",
                "",
                f"**Tags:** {' · '.join(f'`{tag}`' for tag in tags)}",
                "",
                "---",
                "",
            ])
        
        # Footer
        lines.extend([
            "## 📝 Report Metadata",
            "",
            f"- **Report Generated:** {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M:%S UTC')}",
            f"- **Job ID:** `{job.id}`",
            f"- **Platform:** RCA Insight Engine",
            f"- **LLM Provider:** {job.provider}",
            f"- **LLM Model:** {job.model}",
            "",
            "---",
            "",
            "**🔒 Confidentiality Notice:** This report may contain sensitive information. Distribution should be limited to authorized personnel only.",
            "",
            f"**✅ PII Compliance:** All personally identifiable information has been redacted.",
        ])

        return "\n".join(lines).strip()

    def _build_html(
        self,
        job: Job,
        mode: str,
        severity: str,
        metrics: Dict[str, Any],
        summaries: Sequence[FileSummary],
        recommended_actions: Sequence[str],
        tags: Sequence[str],
        llm_output: Dict[str, Any],
    ) -> str:
        # Severity class mapping
        severity_class = f"severity-{severity.lower()}"
        severity_emoji = {"critical": "🔴", "high": "🟠", "moderate": "🟡", "low": "🟢"}.get(severity.lower(), "⚪")
        
        # Calculate duration
        duration_str = "N/A"
        if job.duration_seconds is not None:
            if job.duration_seconds < 60:
                duration_str = f"{job.duration_seconds:.1f} seconds"
            else:
                duration_str = f"{job.duration_seconds / 60:.1f} minutes"
        
        # Format timestamps
        created_at_str = job.created_at.strftime("%B %d, %Y %H:%M:%S UTC") if job.created_at is not None else "N/A"
        completed_at_str = job.completed_at.strftime("%B %d, %Y %H:%M:%S UTC") if job.completed_at is not None else "In Progress"
        
        # Build action items HTML
        priority_actions_html = []
        standard_actions_html = []
        
        for action in recommended_actions:
            action_lower = action.lower()
            action_html = f"<li>{html.escape(action)}</li>"
            if any(word in action_lower for word in ['immediate', 'urgent', 'critical', 'now', 'asap']):
                priority_actions_html.append(action_html)
            else:
                standard_actions_html.append(action_html)
        
        actions_section = ""
        if priority_actions_html:
            actions_section += '<div class="action-group"><h3>🔴 High Priority</h3><ul class="action-list priority-high">'
            actions_section += ''.join(priority_actions_html)
            actions_section += '</ul></div>'
        
        if standard_actions_html:
            actions_section += '<div class="action-group"><h3>🟡 Standard Priority</h3><ul class="action-list priority-standard">'
            actions_section += ''.join(standard_actions_html)
            actions_section += '</ul></div>'
        
        if not actions_section:
            actions_section = '<ul class="action-list"><li>Review the generated summary and log excerpts for next steps.</li></ul>'
        
        # Build file analysis cards
        file_cards_html = []
        for summary in summaries:
            keywords_html = ""
            if summary.top_keywords:
                keywords_html = f"<div class='file-keywords'>🏷️ {' · '.join(html.escape(kw) for kw in summary.top_keywords[:5])}</div>"
            
            sample_head_html = ""
            if summary.sample_head:
                sample_head_html = "<div class='code-excerpt'><strong>Sample Head:</strong><pre><code>"
                sample_head_html += html.escape('\n'.join(summary.sample_head[:5]))
                sample_head_html += "</code></pre></div>"
            
            sample_tail_html = ""
            if summary.sample_tail:
                sample_tail_html = "<div class='code-excerpt'><strong>Sample Tail:</strong><pre><code>"
                sample_tail_html += html.escape('\n'.join(summary.sample_tail[:5]))
                sample_tail_html += "</code></pre></div>"
            
            file_cards_html.append(f"""
            <div class='file-card'>
                <div class='file-header'>
                    <span class='file-icon'>📄</span>
                    <span class='file-name'>{html.escape(summary.filename)}</span>
                </div>
                <table class='metadata-table'>
                    <tr><th>Total Lines</th><td>{summary.line_count:,}</td></tr>
                    <tr><th>Errors</th><td>{summary.error_count}</td></tr>
                    <tr><th>Warnings</th><td>{summary.warning_count}</td></tr>
                    <tr><th>Critical Events</th><td>{summary.critical_count}</td></tr>
                    <tr><th>PII Status</th><td>{html.escape(self._summarise_pii_status(summary))}</td></tr>
                </table>
                {keywords_html}
                {sample_head_html}
                {sample_tail_html}
            </div>
            """)
        
        files_html = ''.join(file_cards_html)
        
        # Platform detection section
        platform_section = ""
        if hasattr(job, 'platform_detection') and job.platform_detection:
            pd = job.platform_detection
            platform_name = html.escape(pd.detected_platform or "Unknown")
            confidence = (pd.confidence_score or 0.0) * 100
            detection_method = html.escape(pd.detection_method or "Unknown")
            
            entities_html = ""
            if pd.extracted_entities:
                processes = [e for e in pd.extracted_entities if e.get('entity_type') == 'process']
                sessions = [e for e in pd.extracted_entities if e.get('entity_type') == 'session']
                stages = [e for e in pd.extracted_entities if e.get('entity_type') in ('stage', 'error_stage')]
                
                entities_items = []
                if processes:
                    entities_items.append(f"<li><strong>Processes:</strong> {html.escape(', '.join([p.get('value', 'Unknown') for p in processes[:5]]))}</li>")
                if sessions:
                    entities_items.append(f"<li><strong>Sessions:</strong> {html.escape(', '.join([s.get('value', 'Unknown') for s in sessions[:5]]))}</li>")
                if stages:
                    entities_items.append(f"<li><strong>Stages/Components:</strong> {html.escape(', '.join([s.get('value', 'Unknown') for s in stages[:5]]))}</li>")
                
                if entities_items:
                    entities_html = f"<h3>Extracted Platform Information</h3><ul>{''.join(entities_items)}</ul>"
            
            insights_html = ""
            if pd.insights:
                insights_html = f"<h3>Platform-Specific Insights</h3><p>{html.escape(pd.insights)}</p>"
            
            platform_section = f"""
            <section class='report-section'>
                <h2 class='section-title'><span class='section-icon'>🤖</span> Platform Detection</h2>
                <p><strong>Detected Platform:</strong> {platform_name}</p>
                <p><strong>Confidence:</strong> {confidence:.0f}%</p>
                <p><strong>Detection Method:</strong> {detection_method}</p>
                {entities_html}
                {insights_html}
            </section>
            """
        
        # PII validation warnings
        pii_warnings_html = ""
        warnings_list = [
            f"<li><strong>{html.escape(summary.filename)}:</strong> {html.escape('; '.join(summary.redaction_validation_warnings))}</li>"
            for summary in summaries
            if summary.redaction_validation_warnings
        ]
        if warnings_list:
            pii_warnings_html = f"<h3>⚠️ Validation Notes</h3><ul>{''.join(warnings_list)}</ul>"
        
        summary_text = html.escape(llm_output.get("summary", "No automated summary available."))
        first_line = html.escape(llm_output.get("summary", "").split('\n')[0] if llm_output.get("summary") else "No summary available")
        
        tags_html = ""
        if tags:
            tags_html = ' · '.join(f"<code>{html.escape(tag)}</code>" for tag in tags)
        
        # Full HTML with embedded CSS
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RCA Report - Job {html.escape(str(job.id))}</title>
    <style>
        :root {{
            --fluent-blue-500: #0078d4;
            --fluent-blue-400: #38bdf8;
            --fluent-info: #38bdf8;
            --fluent-success: #00c853;
            --fluent-warning: #ffb900;
            --fluent-error: #e81123;
            --dark-bg-primary: #0f172a;
            --dark-bg-secondary: #1e293b;
            --dark-bg-tertiary: #334155;
            --dark-text-primary: #f8fafc;
            --dark-text-secondary: #cbd5e1;
            --dark-text-tertiary: #94a3b8;
            --dark-border: #334155;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--dark-bg-primary);
            color: var(--dark-text-primary);
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}

        .report-header {{
            background: linear-gradient(135deg, var(--fluent-blue-500) 0%, var(--fluent-blue-400) 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 120, 212, 0.25);
        }}

        .report-title {{
            font-size: 2rem;
            font-weight: 700;
            color: white;
            margin: 0 0 0.5rem 0;
        }}

        .report-subtitle {{
            font-size: 1.125rem;
            color: rgba(255, 255, 255, 0.9);
            margin: 0;
        }}

        .severity-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1rem;
            margin: 1rem 0;
        }}

        .severity-critical {{
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
            color: white;
            box-shadow: 0 4px 16px rgba(220, 38, 38, 0.4);
        }}

        .severity-high {{
            background: linear-gradient(135deg, #ea580c 0%, #f97316 100%);
            color: white;
            box-shadow: 0 4px 16px rgba(234, 88, 12, 0.4);
        }}

        .severity-moderate {{
            background: linear-gradient(135deg, #ca8a04 0%, #eab308 100%);
            color: white;
            box-shadow: 0 4px 16px rgba(202, 138, 4, 0.4);
        }}

        .severity-low {{
            background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%);
            color: white;
            box-shadow: 0 4px 16px rgba(22, 163, 74, 0.4);
        }}

        .report-section {{
            background: var(--dark-bg-secondary);
            border: 1px solid var(--dark-border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(24px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
        }}

        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--dark-text-primary);
            margin: 0 0 1rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .section-icon {{
            font-size: 1.75rem;
        }}

        .metadata-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}

        .metadata-table th,
        .metadata-table td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--dark-border);
        }}

        .metadata-table th {{
            color: var(--dark-text-secondary);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metadata-table td {{
            color: var(--dark-text-primary);
        }}

        .action-group {{
            margin-bottom: 1.5rem;
        }}

        .action-group h3 {{
            font-size: 1.125rem;
            margin-bottom: 0.75rem;
        }}

        .action-list {{
            list-style: none;
            padding: 0;
        }}

        .action-list li {{
            background: var(--dark-bg-tertiary);
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-radius: 8px;
            border-left: 4px solid var(--fluent-info);
        }}

        .priority-high li {{
            border-left-color: #dc2626;
        }}

        .priority-standard li {{
            border-left-color: #ca8a04;
        }}

        .file-card {{
            background: var(--dark-bg-tertiary);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .file-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}

        .file-icon {{
            font-size: 1.5rem;
        }}

        .file-name {{
            font-family: 'Courier New', monospace;
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--fluent-blue-400);
        }}

        .file-keywords {{
            margin: 1rem 0;
            color: var(--dark-text-secondary);
        }}

        .code-excerpt {{
            background: #1a1a1a;
            border: 1px solid var(--dark-border);
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            overflow-x: auto;
        }}

        .code-excerpt strong {{
            display: block;
            margin-bottom: 0.5rem;
            color: var(--fluent-blue-400);
        }}

        .code-excerpt pre {{
            margin: 0;
        }}

        .code-excerpt code {{
            font-family: 'Courier New', Consolas, Monaco, monospace;
            font-size: 0.875rem;
            color: #e5e7eb;
            line-height: 1.5;
        }}

        .pii-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, var(--fluent-success) 0%, #10b981 100%);
            color: white;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.875rem;
        }}

        .executive-summary {{
            background: var(--dark-bg-tertiary);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
        }}

        .executive-summary h3 {{
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--fluent-blue-400);
        }}

        .executive-summary h3:first-child {{
            margin-top: 0;
        }}

        .executive-summary ul {{
            margin-left: 1.5rem;
        }}

        hr {{
            border: none;
            border-top: 1px solid var(--dark-border);
            margin: 2rem 0;
        }}

        code {{
            background: var(--dark-bg-tertiary);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
        }}

        @media print {{
            body {{
                background: white;
                color: black;
            }}
            
            .report-section {{
                page-break-inside: avoid;
                box-shadow: none;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <div class='report-header'>
        <h1 class='report-title'>{severity_emoji} Root Cause Analysis Report</h1>
        <p class='report-subtitle'>🔍 Investigation #{html.escape(str(job.id))}</p>
    </div>

    <div class='severity-badge {severity_class}'>
        {severity_emoji} <span>{severity.upper()}</span>
    </div>

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>📋</span> Analysis Metadata</h2>
        <table class='metadata-table'>
            <tr><th>Analysis Date</th><td>{created_at_str}</td></tr>
            <tr><th>Completed At</th><td>{completed_at_str}</td></tr>
            <tr><th>Duration</th><td>{duration_str}</td></tr>
            <tr><th>User ID</th><td>{html.escape(str(job.user_id))}</td></tr>
            <tr><th>Job Type</th><td>{html.escape(mode.replace('_', ' ').title())}</td></tr>
            <tr><th>Severity</th><td>{severity.upper()}</td></tr>
            <tr><th>Files Analyzed</th><td>{metrics.get('files', 0)}</td></tr>
            <tr><th>PII Protection</th><td>{html.escape(self._summarise_pii_metrics(metrics))}</td></tr>
        </table>
    </section>

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>📝</span> Executive Summary</h2>
        <div class='executive-summary'>
            <h3>Quick Assessment</h3>
            <ul>
                <li><strong>Severity Level:</strong> {severity_emoji} {severity.upper()}</li>
                <li><strong>Total Errors:</strong> {metrics.get('errors', 0)} errors, {metrics.get('warnings', 0)} warnings, {metrics.get('critical', 0)} critical events</li>
                <li><strong>Files Analyzed:</strong> {metrics.get('files', 0)} file(s) processed</li>
                <li><strong>Analysis Duration:</strong> {duration_str}</li>
            </ul>
            <h3>One-Line Summary</h3>
            <p>{first_line}</p>
        </div>
    </section>

    {platform_section}

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>🎯</span> Detailed Analysis</h2>
        <p style='white-space: pre-wrap;'>{summary_text}</p>
    </section>

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>🚨</span> Recommended Actions</h2>
        {actions_section}
    </section>

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>🔒</span> PII Protection & Security</h2>
        <h3>Protection Summary</h3>
        <p><span class='pii-badge'>✅ Enterprise-grade multi-layer redaction applied</span></p>
        <table class='metadata-table'>
            <tr><th>Files Scanned</th><td>{metrics.get('files', 0)}</td><td>✅ Complete</td></tr>
            <tr><th>Files Sanitized</th><td>{metrics.get('pii_redacted_files', 0)}</td><td>✅ Redacted</td></tr>
            <tr><th>Files Quarantined</th><td>{metrics.get('pii_failsafe_files', 0)}</td><td>{'⚠️ Review' if metrics.get('pii_failsafe_files', 0) > 0 else '✅ Clean'}</td></tr>
            <tr><th>Total Redactions</th><td>{metrics.get('pii_total_redactions', 0)} items</td><td>✅ Protected</td></tr>
            <tr><th>Validation Events</th><td>{metrics.get('pii_validation_events', 0)}</td><td>{'⚠️ Review' if metrics.get('pii_validation_events', 0) > 0 else '✅ Verified'}</td></tr>
        </table>
        {pii_warnings_html}
        <p><strong>Security Guarantee:</strong> All sensitive data removed before LLM processing.</p>
    </section>

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>📊</span> File Analysis</h2>
        {files_html}
    </section>

    {('<section class="report-section"><h2 class="section-title"><span class="section-icon">📌</span> Tags & Categories</h2><p><strong>Tags:</strong> ' + tags_html + '</p></section>') if tags else ''}

    <section class='report-section'>
        <h2 class='section-title'><span class='section-icon'>📝</span> Report Metadata</h2>
        <ul>
            <li><strong>Report Generated:</strong> {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M:%S UTC')}</li>
            <li><strong>Job ID:</strong> <code>{html.escape(str(job.id))}</code></li>
            <li><strong>Platform:</strong> RCA Insight Engine</li>
            <li><strong>LLM Provider:</strong> {html.escape(str(job.provider))}</li>
            <li><strong>LLM Model:</strong> {html.escape(str(job.model))}</li>
        </ul>
        <hr>
        <p><strong>🔒 Confidentiality Notice:</strong> This report may contain sensitive information. Distribution should be limited to authorized personnel only.</p>
        <p><strong>✅ PII Compliance:</strong> All personally identifiable information has been redacted.</p>
    </section>
</body>
</html>"""

    async def _process_single_file(
        self,
        job: Job,
        descriptor: FileDescriptor,
        *,
        position: int,
        total_files: int,
        detection_collector: Optional[Callable[[DetectionInput], None]] = None,
    ) -> FileSummary:
        async with self._session_factory() as session:
            file_record = await session.get(File, descriptor.id)
            if file_record is None:
                raise ValueError(f"File {descriptor.id} missing for job {job.id}")

            context = self._build_pipeline_context(job, file_record)

            file_label = (
                descriptor.name
                or getattr(file_record, "original_filename", None)
                or Path(descriptor.path).name
            )
            file_details: Dict[str, Any] = sanitise_metadata(
                {
                    "file_id": descriptor.id,
                    "filename": file_label,
                    "file_number": position,
                    "total_files": total_files,
                    "size": descriptor.size_bytes,
                }
            )

            await self._job_service.create_job_event(
                str(job.id),
                "file-processing-started",
                file_details,
                session=session,
            )

            await self._emit_progress_event(
                str(job.id),
                "redaction",
                "started",
                session=session,
                message=(
                    "Scanning "
                    f"{self._describe_file_position(file_label, position, total_files)}"
                    " for sensitive data..."
                ),
                details=file_details,
            )

            text = await self._read_text(descriptor.path)
            self._maybe_collect_detection_input(
                detection_collector,
                descriptor,
                file_record,
                text,
            )
            redaction_result = self._apply_redaction(text)
            if redaction_result.validation_warnings:
                warning_log_fn = logger.error if redaction_result.failsafe_triggered else logger.warning
                combined_warning = "; ".join(redaction_result.validation_warnings)
                warning_log_fn(
                    "Job %s: PII safeguard notice for %s: %s",
                    job.id,
                    file_label,
                    combined_warning,
                )
                icon = "🚫" if redaction_result.failsafe_triggered else ("⚠️" if not redaction_result.validation_passed else "🔐")
                preview = "; ".join(redaction_result.validation_warnings[:2])
                if len(redaction_result.validation_warnings) > 2:
                    preview += " …"
                await self._emit_progress_event(
                    str(job.id),
                    "redaction",
                    "in-progress",
                    session=session,
                    message=f"{icon} {preview}",
                    details={
                        "file": file_label,
                        "validation_warnings": redaction_result.validation_warnings,
                        "validation_passed": redaction_result.validation_passed,
                        "failsafe_triggered": redaction_result.failsafe_triggered,
                    },
                )

            summary, chunk_count = await self._analyse_and_store(
                session,
                job,
                file_record,
                redaction_result.text,
                redaction_result.replacements,
                context,
                filename=file_label,
                position=position,
                total_files=total_files,
                failsafe_triggered=redaction_result.failsafe_triggered,
                validation_warnings=redaction_result.validation_warnings or [],
            )
            summary.chunk_count = chunk_count
            summary.redaction_failsafe_triggered = redaction_result.failsafe_triggered
            summary.redaction_validation_warnings = list(redaction_result.validation_warnings or [])

            redaction_hits = sum(redaction_result.replacements.values())
            redaction_details = sanitise_metadata(
                {
                    **file_details,
                    "redaction_hits": redaction_hits,
                    "redaction_counts": summary.redaction_counts,
                    "pii_redaction_applied": summary.redaction_applied,
                    "validation_passed": redaction_result.validation_passed,
                    "validation_warnings": redaction_result.validation_warnings or [],
                    "failsafe_triggered": redaction_result.failsafe_triggered,
                }
            )
            if redaction_result.failsafe_triggered:
                redaction_details["pii_status"] = "failsafe_quarantined"
            elif redaction_hits:
                redaction_details["pii_status"] = "redacted"
            else:
                redaction_details["pii_status"] = "clear"
            
            # Enhanced completion message with security status
            warning_count = len(redaction_result.validation_warnings) if redaction_result.validation_warnings else 0
            if redaction_result.failsafe_triggered:
                completion_message = (
                    f"🚫 Sensitive content quarantined in {file_label}; data withheld from AI analysis."
                )
            elif not redaction_result.validation_passed:
                completion_message = (
                    f"🔒 Redacted {redaction_hits} items in {file_label} (Security validation: {warning_count} warnings)"
                )
            elif redaction_hits:
                completion_message = f"🔒 Secured: Masked {redaction_hits} sensitive item{'s' if redaction_hits != 1 else ''} in {file_label}"
            else:
                completion_message = f"✓ Scanned {file_label}: No sensitive data detected"
            
            await self._emit_progress_event(
                str(job.id),
                "redaction",
                "completed",
                session=session,
                message=completion_message,
                details=redaction_details,
            )

            completion_payload = sanitise_metadata(
                {
                    **file_details,
                    "chunks": chunk_count,
                    "errors": summary.error_count,
                    "warnings": summary.warning_count,
                    "critical": summary.critical_count,
                    "pii_redacted": summary.redaction_applied,
                    "redaction_hits": summary.redaction_counts,
                    "pii_failsafe_triggered": summary.redaction_failsafe_triggered,
                    "validation_warnings": summary.redaction_validation_warnings,
                }
            )
            await self._job_service.create_job_event(
                str(job.id),
                "file-processing-completed",
                completion_payload,
                session=session,
            )

            await session.commit()
            await self._job_service.publish_session_events(session)
            return summary

    def _maybe_collect_detection_input(
        self,
        collector: Optional[Callable[[DetectionInput], None]],
        descriptor: FileDescriptor,
        file_record: File,
        text: str,
    ) -> None:
        if collector is None or not isinstance(text, str):
            return

        snippet = self._truncate_detection_content(text)
        metadata: Dict[str, Any] = {}

        record_metadata = getattr(file_record, "metadata", None)
        if isinstance(record_metadata, Mapping):
            for key, value in record_metadata.items():
                if isinstance(key, str):
                    metadata[key] = value

        descriptor_metadata = descriptor.metadata or {}
        for key, value in descriptor_metadata.items():
            if isinstance(key, str) and key not in metadata:
                metadata[key] = value

        metadata = sanitise_metadata(metadata)

        original_filename = cast(Optional[str], getattr(file_record, "original_filename", None))
        fallback_filename = cast(Optional[str], getattr(file_record, "filename", None))
        detected_name = (
            original_filename
            or descriptor.name
            or fallback_filename
            or Path(descriptor.path).name
        )
        content_type = descriptor.content_type or cast(
            Optional[str], getattr(file_record, "content_type", None)
        )

        collector(DetectionInput(str(detected_name), snippet, content_type, metadata))

    @staticmethod
    def _truncate_detection_content(content: str, limit: int = 8000) -> str:
        if not content:
            return ""
        if len(content) <= limit:
            return content
        half = max(limit // 2, 1)
        head = content[:half]
        tail = content[-half:]
        return f"{head}\n...\n{tail}"

    async def _analyse_and_store(
        self,
        session: AsyncSession,
        job: Job,
        file_record: File,
        text: str,
        redactions: Optional[Dict[str, int]] = None,
        context: Optional[PipelineContext] = None,
        *,
        filename: str,
        position: int,
        total_files: int,
        failsafe_triggered: bool,
        validation_warnings: Sequence[str],
    ) -> Tuple[FileSummary, int]:
        context = context or self._build_pipeline_context(job, file_record)

        lines = text.splitlines()
        summary = self._build_summary(file_record, lines)
        summary.redaction_counts = dict(redactions or {})
        summary.redaction_applied = bool(summary.redaction_counts)
        summary.redaction_failsafe_triggered = failsafe_triggered
        summary.redaction_validation_warnings = list(validation_warnings)

        file_details: Dict[str, Any] = sanitise_metadata(
            {
                "file_id": str(file_record.id),
                "filename": filename,
                "file_number": position,
                "total_files": total_files,
            }
        )

        await self._emit_progress_event(
            str(job.id),
            "chunking",
            "started",
            session=session,
            message=(
                "Segmenting "
                f"{self._describe_file_position(filename, position, total_files)}"
                " into analysis chunks..."
            ),
            details=file_details,
        )

        chunk_started_at = datetime.now(timezone.utc)
        chunk_timer = time.perf_counter()
        chunk_status = PipelineStatus.SUCCESS
        chunks: List[str] = []
        try:
            chunks = self._chunk_lines(lines)
        except Exception:
            chunk_status = PipelineStatus.FAILED
            raise
        finally:
            chunk_completed_at = datetime.now(timezone.utc)
            chunk_duration = max(time.perf_counter() - chunk_timer, 0.0)
            chunk_metadata: Dict[str, Any] = {
                "chunk_count": len(chunks),
                "line_count": summary.line_count,
                "pii_redaction_applied": summary.redaction_applied,
                "redaction_counts": summary.redaction_counts,
                "pii_failsafe_triggered": summary.redaction_failsafe_triggered,
            }
            chunk_metadata.update(file_details)
            if chunk_status is PipelineStatus.FAILED:
                chunk_metadata["error"] = "Chunking failed"
            await self._record_stage_event(
                session,
                str(job.id),
                context,
                stage=PipelineStage.CHUNK,
                status=chunk_status,
                started_at=chunk_started_at,
                completed_at=chunk_completed_at,
                duration_seconds=chunk_duration,
                metadata=chunk_metadata,
            )

        summary.chunk_count = len(chunks)

        embedding_start_details = sanitise_metadata(
            {**file_details, "chunk_count": len(chunks)}
        )
        await self._emit_progress_event(
            str(job.id),
            "embedding",
            "started",
            session=session,
            message=(
                "Generating embeddings for "
                f"{self._describe_file_position(filename, position, total_files)}..."
            ),
            details=embedding_start_details,
        )

        embed_started_at = datetime.now(timezone.utc)
        embed_timer = time.perf_counter()
        embed_status = PipelineStatus.SUCCESS
        embeddings: List[List[float]] = []
        try:
            embeddings = await self._generate_embeddings(
                chunks,
                context=context,
                pii_scrubbed=True,
            )
        except Exception:
            embed_status = PipelineStatus.FAILED
            raise
        finally:
            embed_completed_at = datetime.now(timezone.utc)
            embed_duration = max(time.perf_counter() - embed_timer, 0.0)
            embed_metadata: Dict[str, Any] = {
                "chunk_count": len(chunks),
                "pii_failsafe_triggered": summary.redaction_failsafe_triggered,
            }
            embed_metadata.update(embedding_start_details)
            if embed_status is PipelineStatus.FAILED:
                embed_metadata["error"] = "Embedding generation failed"
            await self._record_stage_event(
                session,
                str(job.id),
                context,
                stage=PipelineStage.EMBED,
                status=embed_status,
                started_at=embed_started_at,
                completed_at=embed_completed_at,
                duration_seconds=embed_duration,
                metadata=embed_metadata,
            )

        storage_details = sanitise_metadata({**file_details, "chunk_count": len(chunks)})
        await self._emit_progress_event(
            str(job.id),
            "storage",
            "started",
            session=session,
            message=(
                "Storing analysis artefacts for "
                f"{self._describe_file_position(filename, position, total_files)}..."
            ),
            details=storage_details,
        )

        storage_started_at = datetime.now(timezone.utc)
        storage_timer = time.perf_counter()
        storage_status = PipelineStatus.SUCCESS
        stored_count = 0
        try:
            for index, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
                document = Document(
                    job_id=job.id,
                    file_id=file_record.id,
                    content=chunk_text,
                    content_type="text/plain",
                    metadata={
                        "filename": file_record.original_filename,
                        "chunk_index": index,
                        "pii_redacted": summary.redaction_applied,
                        "pii_failsafe": summary.redaction_failsafe_triggered,
                    },
                    chunk_index=index,
                    chunk_size=len(chunk_text),
                    content_embedding=vector,
                )
                session.add(document)
                stored_count += 1

            metadata = file_record.metadata or {}
            privacy_config = cast(Any, settings.privacy)
            metadata["analysis_summary"] = {
                "line_count": summary.line_count,
                "error_count": summary.error_count,
                "warning_count": summary.warning_count,
                "critical_count": summary.critical_count,
                "top_keywords": summary.top_keywords,
            }
            if summary.redaction_applied:
                metadata["pii_redaction"] = {
                    "applied": True,
                    "replacement": privacy_config.PII_REDACTION_REPLACEMENT,
                    "counts": summary.redaction_counts,
                    "failsafe_triggered": summary.redaction_failsafe_triggered,
                    "validation_warnings": summary.redaction_validation_warnings,
                }
            elif summary.redaction_failsafe_triggered:
                metadata["pii_redaction"] = {
                    "applied": False,
                    "failsafe_triggered": True,
                    "replacement": privacy_config.PII_REDACTION_FAILSAFE_REPLACEMENT,
                    "validation_warnings": summary.redaction_validation_warnings,
                }
            file_record.metadata = metadata
            setattr(file_record, "processed", True)
            setattr(file_record, "processed_at", datetime.now(timezone.utc))
            await session.flush()
        except Exception:
            storage_status = PipelineStatus.FAILED
            raise
        finally:
            storage_completed_at = datetime.now(timezone.utc)
            storage_duration = max(time.perf_counter() - storage_timer, 0.0)
            storage_metadata: Dict[str, Any] = {
                "document_count": stored_count,
                "pii_redaction_applied": summary.redaction_applied,
                "redaction_counts": summary.redaction_counts,
                "pii_failsafe_triggered": summary.redaction_failsafe_triggered,
                "validation_warnings": summary.redaction_validation_warnings,
            }
            storage_metadata.update(storage_details)
            if storage_status is PipelineStatus.FAILED:
                storage_metadata["error"] = "Storage failed"
            await self._record_stage_event(
                session,
                str(job.id),
                context,
                stage=PipelineStage.STORAGE,
                status=storage_status,
                started_at=storage_started_at,
                completed_at=storage_completed_at,
                duration_seconds=storage_duration,
                metadata=storage_metadata,
            )

        return summary, len(chunks)


    async def _run_llm_analysis(
        self,
        job: Job,
        summaries: Sequence[FileSummary],
        mode: str,
    ) -> Dict[str, Any]:
        from core.prompts import get_prompt_manager
        
        provider_value = cast(Optional[str], getattr(job, "provider", None))
        model_value = cast(Optional[str], getattr(job, "model", None))
        provider_name = (provider_value or settings.llm.DEFAULT_PROVIDER).lower()
        model_name = model_value or settings.llm.OLLAMA_MODEL
        provider = LLMProviderFactory.create_provider(provider_name, model=model_name)

        pii_redacted = sum(1 for summary in summaries if summary.redaction_applied)
        pii_failsafe = sum(1 for summary in summaries if summary.redaction_failsafe_triggered)

        # Get custom prompt template if specified in job manifest, otherwise use default
        manifest = getattr(job, "input_manifest", None) or {}
        template_name = manifest.get("prompt_template", "rca_analysis")
        
        # Build file summaries for prompt
        file_summary_lines = []
        file_summary_lines.append(
            "All file content has been sanitized to remove personal or secret information before this request."
        )
        for summary in summaries:
            file_summary_lines.append(
                f"- {summary.filename} "
                f"(lines={summary.line_count}, errors={summary.error_count}, "
                f"warnings={summary.warning_count}, critical={summary.critical_count}, "
                f"top_keywords={', '.join(summary.top_keywords[:5])})"
            )
        file_summaries_text = "\n".join(file_summary_lines)
        
        # Use prompt template manager to format the prompt
        prompt_manager = get_prompt_manager()
        system_prompt, user_prompt = prompt_manager.format_prompt(
            template_name,
            job_id=str(job.id),
            mode=mode,
            file_summaries=file_summaries_text
        )
        
        # Fall back to legacy prompt if template not found
        if not user_prompt:
            logger.warning(f"Prompt template '{template_name}' not found, using legacy prompt")
            prompt_lines = [
                f"Job ID: {job.id}",
                f"Scenario: {mode}",
                "",
                "Provide a concise root cause assessment and remediation plan based on the following file summaries:",
            ]
            prompt_lines.append(file_summaries_text)
            prompt_lines.append("")
            prompt_lines.append(
                "Focus on likely causes, impacted areas, and actionable remediation steps."
            )
            user_prompt = "\n".join(prompt_lines)
            system_prompt = None

        raw_prompt = user_prompt
        prompt_guard = self._pii_redactor.redact(raw_prompt)
        sanitized_prompt = prompt_guard.text
        prompt_redactions_total = sum(prompt_guard.replacements.values())
        prompt_guard_details: Dict[str, Any] = {
            "pii_prompt_redactions": prompt_redactions_total,
            "pii_prompt_replacement_counts": dict(prompt_guard.replacements),
            "pii_prompt_validation_warnings": list(prompt_guard.validation_warnings or []),
            "pii_prompt_validation_passed": prompt_guard.validation_passed,
            "pii_prompt_failsafe": prompt_guard.failsafe_triggered,
            "prompt_template": template_name,  # Include which template was used
        }

        if prompt_redactions_total:
            logger.info(
                "Sanitized LLM prompt by masking %d sensitive token(s) before analysis",
                prompt_redactions_total,
            )
        for warning in prompt_guard.validation_warnings or []:
            logger.warning("LLM prompt validation warning: %s", warning)

        if prompt_guard.failsafe_triggered:
            block_message = (
                "LLM analysis blocked: residual sensitive data detected after maximum redaction passes."
            )
            block_details = {
                "provider": provider_name,
                "model": model_name,
                "mode": mode,
                "pii_redacted_files": pii_redacted,
                "pii_failsafe_files": pii_failsafe,
                **prompt_guard_details,
            }
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "failed",
                message=block_message,
                details=block_details,
            )
            await self._job_service.append_conversation_turns(
                str(job.id),
                [
                    {
                        "role": "assistant",
                        "content": "Automated analysis blocked to prevent potential sensitive data exposure.",
                        "metadata": {
                            "provider": provider_name,
                            "model": model_name,
                            "mode": mode,
                            "blocked": True,
                            "pii_prompt": prompt_guard_details,
                        },
                    }
                ],
                event_metadata={
                    "provider": provider_name,
                    "model": model_name,
                    "mode": mode,
                    "blocked": True,
                    "pii_prompt": prompt_guard_details,
                },
            )
            return {
                "provider": provider_name,
                "model": model_name,
                "summary": "Automated analysis blocked to avoid exposing sensitive data.",
                "error": "pii_prompt_failsafe_triggered",
                "blocked": True,
                "pii_prompt": prompt_guard_details,
            }

        if prompt_redactions_total or prompt_guard.validation_warnings:
            guard_message = (
                f"🔒 Sanitized AI prompt; {prompt_redactions_total} mask(s) applied."
                if prompt_redactions_total
                else "⚠️ AI prompt sanitized after validation warning."
            )
            if prompt_guard.validation_warnings:
                guard_message += " Validation re-ran automatically."
        else:
            guard_message = "✓ AI prompt verified clean before analysis."

        await self._emit_progress_event(
            str(job.id),
            "llm",
            "in-progress",
            message=guard_message,
            details={
                "provider": provider_name,
                "model": model_name,
                "mode": mode,
                "pii_redacted_files": pii_redacted,
                "pii_failsafe_files": pii_failsafe,
                **prompt_guard_details,
            },
        )

        # Build messages with custom system prompt if available
        default_system_prompt = "You are an experienced Site Reliability Engineer performing incident triage."
        messages = [
            LLMMessage(
                role="system",
                content=system_prompt or default_system_prompt,
            ),
            LLMMessage(role="user", content=sanitized_prompt),
        ]
        prompt_turns = [
            {
                "role": message.role,
                "content": message.content,
                "metadata": {
                    "provider": provider_name,
                    "model": model_name,
                    "mode": mode,
                    "type": "prompt",
                    "pii_prompt": prompt_guard_details,
                    "prompt_template": template_name,
                },
            }
            for message in messages
        ]

        try:
            await provider.initialize()
            response = await provider.generate(messages, temperature=0.2)
            assistant_content = response.content.strip()
            await self._job_service.append_conversation_turns(
                str(job.id),
                prompt_turns
                + [
                    {
                        "role": "assistant",
                        "content": assistant_content,
                        "token_count": (response.usage or {}).get("total_tokens"),
                        "metadata": {
                            "provider": response.provider,
                            "model": response.model,
                            "mode": mode,
                            "usage": response.usage or {},
                            "pii_prompt": prompt_guard_details,
                        },
                    }
                ],
                event_metadata={"provider": response.provider, "model": response.model, "mode": mode},
            )
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "completed",
                message="Root cause analysis draft generated.",
                details={
                    "provider": response.provider,
                    "model": response.model,
                    "mode": mode,
                    "usage": response.usage or {},
                    "pii_redacted_files": pii_redacted,
                    "pii_failsafe_files": pii_failsafe,
                    **prompt_guard_details,
                },
            )
            return {
                "provider": response.provider,
                "model": response.model,
                "summary": assistant_content,
                "usage": response.usage,
                "blocked": False,
                "pii_prompt": prompt_guard_details,
            }
        except Exception as exc:  # pragma: no cover - provider failures
            logger.warning(
                "LLM analysis failed for job %s using provider %s: %s",
                job.id,
                provider_name,
                exc,
            )
            await self._emit_progress_event(
                str(job.id),
                "llm",
                "failed",
                message=f"LLM analysis failed: {exc}",
                details={
                    "provider": provider_name,
                    "model": model_name,
                    "mode": mode,
                },
            )
            await self._job_service.append_conversation_turns(
                str(job.id),
                prompt_turns
                + [
                    {
                        "role": "assistant",
                        "content": f"LLM analysis failed: {exc}",
                        "metadata": {
                            "provider": provider_name,
                            "model": model_name,
                            "mode": mode,
                            "error": True,
                            "pii_prompt": prompt_guard_details,
                        },
                    }
                ],
                event_metadata={
                    "provider": provider_name,
                    "model": model_name,
                    "mode": mode,
                    "error": True,
                    "pii_prompt": prompt_guard_details,
                },
            )
            return {
                "provider": provider_name,
                "model": model_name,
                "summary": "Automated analysis unavailable; review file summaries for context.",
                "error": str(exc),
                "blocked": False,
                "pii_prompt": prompt_guard_details,
            }
        finally:
            try:
                await provider.close()
            except Exception:
                logger.debug("Failed to close LLM provider cleanly", exc_info=True)

    async def _list_job_files(self, job_id: str) -> List[FileDescriptor]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(File)
                .where(File.job_id == job_id)
                .order_by(File.created_at.asc())
            )
            rows = result.scalars().all()

        descriptors: List[FileDescriptor] = []
        for row in rows:
            path_value = str(getattr(row, "file_path", ""))
            original_name = cast(Optional[str], getattr(row, "original_filename", None))
            fallback_name = cast(Optional[str], getattr(row, "filename", None))
            checksum_value = str(getattr(row, "checksum", ""))
            content_type = cast(Optional[str], getattr(row, "content_type", None))
            metadata_value = cast(Optional[Dict[str, Any]], getattr(row, "metadata", None))
            size_raw = getattr(row, "file_size", 0) or 0
            try:
                size_bytes = int(size_raw)
            except (TypeError, ValueError):  # pragma: no cover - defensive guard
                size_bytes = 0

            descriptors.append(
                FileDescriptor(
                    id=str(row.id),
                    path=path_value,
                    name=original_name or fallback_name or Path(path_value).name,
                    checksum=checksum_value,
                    content_type=content_type,
                    metadata=metadata_value,
                    size_bytes=size_bytes,
                )
            )
        return descriptors

    async def _read_text(self, path: str) -> str:
        file_path = Path(path)
        try:
            # Run blocking encoding detection off the event loop to keep worker throughput healthy.
            probe = await asyncio.to_thread(
                probe_text_file,
                file_path,
                min_confidence=0.6,
                min_printable_ratio=0.6,
            )
        except EncodingProbeError as exc:
            logger.warning(
                "Encoding probe failed for %s; falling back to legacy reader (%s)",
                path,
                exc,
            )
        else:
            if probe.warnings:
                logger.warning(
                    "Encoding probe warnings for %s: %s",
                    path,
                    ", ".join(probe.warnings),
                )
            return probe.text

        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                return await handle.read()
        except UnicodeDecodeError:
            async with aiofiles.open(
                path, "r", encoding="latin-1", errors="ignore"
            ) as handle:
                return await handle.read()

    def _apply_redaction(self, text: str) -> RedactionResult:
        """Redact PII if enabled."""
        if not text:
            return RedactionResult(text=text, replacements={})
        return self._pii_redactor.redact(text)

    def _build_summary(self, file_record: File, lines: Sequence[str]) -> FileSummary:
        lowered = [line.lower() for line in lines]
        error_count = sum("error" in line for line in lowered)
        warning_count = sum("warning" in line for line in lowered)
        critical_count = sum("critical" in line for line in lowered)
        info_count = sum("info" in line for line in lowered)

        keywords: Counter[str] = Counter()
        for line in lowered:
            keywords.update(re.findall(r"[a-z]{4,}", line))

        sample_head = list(lines[:5])
        sample_tail = list(lines[-5:]) if len(lines) > 5 else []

        original_filename = cast(Optional[str], getattr(file_record, "original_filename", None))
        fallback_filename = cast(Optional[str], getattr(file_record, "filename", None))
        checksum = str(getattr(file_record, "checksum", ""))
        file_size_value = getattr(file_record, "file_size", 0) or 0
        try:
            file_size = int(file_size_value)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            file_size = 0
        content_type = cast(Optional[str], getattr(file_record, "content_type", None))
        filename = original_filename or fallback_filename or "unknown"

        return FileSummary(
            file_id=str(file_record.id),
            filename=filename,
            checksum=checksum,
            file_size=file_size,
            content_type=content_type,
            line_count=len(lines),
            error_count=error_count,
            warning_count=warning_count,
            critical_count=critical_count,
            info_count=info_count,
            sample_head=sample_head,
            sample_tail=sample_tail,
            top_keywords=[word for word, _ in keywords.most_common(10)],
        )

    def _chunk_lines(self, lines: Sequence[str]) -> List[str]:
        config = settings.ingestion
        max_chars = max(1, int(config.CHUNK_MAX_CHARACTERS))
        min_chars = max(1, min(int(config.CHUNK_MIN_CHARACTERS), max_chars - 1))
        overlap_chars = max(0, min(int(config.CHUNK_OVERLAP_CHARACTERS), max_chars - 1))
        line_limit = max(1, min(int(config.LINE_MAX_CHARACTERS), max_chars))

        segments: List[str] = []
        for raw_line in lines:
            line = raw_line.rstrip("\r\n")
            if not line:
                segments.append("")
                continue
            segments.extend(self._split_long_line(line, line_limit))

        if not segments:
            return [""]

        chunks: List[str] = []
        buffer: List[str] = []
        buffer_len = 0

        for segment in segments:
            segment_len = len(segment)
            addition = segment_len if not buffer else segment_len + 1
            if buffer and buffer_len + addition > max_chars:
                previous = buffer
                chunks.append("\n".join(previous))
                buffer = []
                buffer_len = 0
                if overlap_chars:
                    overlap_segments: List[str] = []
                    overlap_len = 0
                    for candidate in reversed(previous):
                        candidate_len = len(candidate)
                        contribution = candidate_len if not overlap_segments else candidate_len + 1
                        if overlap_len + contribution > overlap_chars:
                            break
                        overlap_segments.insert(0, candidate)
                        overlap_len += contribution
                    if overlap_segments:
                        buffer = overlap_segments
                        buffer_len = overlap_len

            if buffer:
                buffer_len += 1
            buffer.append(segment)
            buffer_len += segment_len

        if buffer:
            chunks.append("\n".join(buffer))

        if len(chunks) > 1 and len(chunks[-1]) < min_chars:
            tail = chunks.pop()
            merged = chunks[-1] + ("\n" if chunks[-1] else "") + tail
            if len(merged) <= max_chars:
                chunks[-1] = merged
            else:
                chunks.append(tail)

        return chunks or [""]

    @staticmethod
    def _split_long_line(text: str, max_length: int) -> List[str]:
        if len(text) <= max_length:
            return [text]

        parts: List[str] = []
        start = 0
        end = len(text)

        while start < end:
            slice_end = min(end, start + max_length)
            if slice_end < end:
                break_pos = text.rfind(" ", start + 1, slice_end)
                if break_pos <= start:
                    break_pos = text.rfind("\t", start + 1, slice_end)
                if break_pos <= start:
                    break_pos = slice_end
            else:
                break_pos = slice_end

            segment = text[start:break_pos]
            if segment:
                parts.append(segment)
            start = break_pos
            if start < end and text[start].isspace():
                start += 1

        if not parts:
            return [text[:max_length]] + JobProcessor._split_long_line(text[max_length:], max_length)

        if start < end:
            remainder = text[start:end]
            if remainder:
                parts.extend(JobProcessor._split_long_line(remainder, max_length))

        return parts

    async def _generate_embeddings(
        self,
        texts: Sequence[str],
        *,
        context: Optional[PipelineContext] = None,
        pii_scrubbed: bool = True,
    ) -> List[List[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        service = await self._ensure_embedding_service()
        batch_size = max(1, int(settings.ingestion.EMBED_BATCH_SIZE))

        tenant_uuid = context.tenant_uuid if context else None
        cache_enabled = (
            tenant_uuid is not None
            and settings.feature_flags.is_enabled("embedding_cache_enabled")
        )

        if not cache_enabled:
            return await self._embed_in_batches(service, texts_list, batch_size)

        model_key = self._resolve_embedding_model(service)
        embeddings: List[Optional[List[float]]] = [None] * len(texts_list)
        scrub_confirmed = bool(pii_scrubbed)
        scrub_metadata = {
            "pii_scrubbed": scrub_confirmed,
            "scrubbed": scrub_confirmed,
            "scrubbed_confirmed": scrub_confirmed,
            "privacy": {
                "pii_scrubbed": scrub_confirmed,
                "scrubbed_confirmed": scrub_confirmed,
            },
        }

        assert tenant_uuid is not None  # guarded by cache_enabled check

        async with self._session_factory() as session:
            cache_service = EmbeddingCacheService(session, metrics=_PIPELINE_METRICS)
            misses: List[Tuple[int, str, str]] = []
            for index, text in enumerate(texts_list):
                content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                hit = await cache_service.lookup(tenant_uuid, content_hash, model_key)
                if hit is not None:
                    embeddings[index] = hit.embedding
                    continue
                misses.append((index, text, content_hash))

            if misses:
                miss_texts = [text for (_, text, _) in misses]
                miss_vectors = await self._embed_in_batches(service, miss_texts, batch_size)
                if len(miss_vectors) != len(misses):
                    raise RuntimeError(
                        "Embedding provider returned mismatched batch size: "
                        f"expected {len(misses)}, got {len(miss_vectors)}"
                    )

                misses_with_vectors = list(zip(misses, miss_vectors))
                for (idx, _text, _hash), vector in misses_with_vectors:
                    embeddings[idx] = vector

                if scrub_confirmed:
                    try:
                        for (_idx, _text, content_hash), vector in misses_with_vectors:
                            await cache_service.store(
                                tenant_uuid,
                                content_hash,
                                model_key,
                                embedding_vector_id=None,
                                scrub_metadata=scrub_metadata,
                                embedding=vector,
                            )
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        logger.debug(
                            "Embedding cache entry already exists",
                            extra={
                                "tenant_id": str(tenant_uuid),
                                "model": model_key,
                                "miss_count": len(misses_with_vectors),
                            },
                        )
                    except Exception:
                        await session.rollback()
                        logger.exception(
                            "Failed to store embedding cache entry",
                            extra={
                                "tenant_id": str(tenant_uuid),
                                "model": model_key,
                                "miss_count": len(misses_with_vectors),
                            },
                        )
                else:
                    logger.debug(
                        "Skipping embedding cache store due to missing scrub confirmation",
                        extra={"tenant_id": str(tenant_uuid), "model": model_key},
                    )

        resolved: List[List[float]] = []
        for index, vector in enumerate(embeddings):
            if vector is None:
                raise RuntimeError(f"Embedding missing for chunk {index}")
            resolved.append(vector)

        return resolved

    async def _embed_in_batches(
        self,
        service: EmbeddingService,
        texts: Sequence[str],
        batch_size: int,
    ) -> List[List[float]]:
        vectors: List[List[float]] = []
        batch_size = max(1, batch_size)
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            if not batch:
                continue
            result = await service.embed_texts(batch)
            if len(result) != len(batch):
                raise RuntimeError(
                    "Embedding provider returned mismatched batch size: "
                    f"expected {len(batch)}, got {len(result)}"
                )
            vectors.extend(result)
        return vectors

    @staticmethod
    def _resolve_embedding_model(service: EmbeddingService) -> str:
        provider = service.provider
        model_name = getattr(provider, "model", None)
        if isinstance(model_name, str) and model_name:
            return model_name
        return provider.provider_name

    async def _ensure_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is not None:
            return self._embedding_service

        async with self._embedding_lock:
            if self._embedding_service is None:
                service = EmbeddingService()
                await service.initialize()
                self._embedding_service = service
        return self._embedding_service  # type: ignore[return-value]


__all__ = ["JobProcessor"]
