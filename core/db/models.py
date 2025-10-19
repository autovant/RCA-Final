"""
Database models for the RCA Engine.
Includes job orchestration primitives, conversation traceability, ticket
metadata, and watcher configuration as outlined in the PRD.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates, synonym
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from core.config import settings

Base = declarative_base()


class Job(Base):
    """Top-level RCA job representation."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)

    # User context
    user_id = Column(String(100), nullable=False, index=True)

    # Job configuration
    input_manifest = Column(JSON, nullable=False)
    provider = Column(String(50), nullable=False, default="ollama")
    model = Column(String(100), nullable=False, default="llama2")
    model_config = Column(JSON, default=dict)

    # Operational metadata
    priority = Column(Integer, default=0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Timeline
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Results and lineage
    result_data = Column(JSON)
    outputs = Column(JSON, default=dict)
    ticketing = Column(JSON, default=dict)
    source = Column(JSON)
    error_message = Column(Text)

    events = relationship(
        "JobEvent", back_populates="job", cascade="all, delete-orphan"
    )
    files = relationship(
        "File", back_populates="job", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="job", cascade="all, delete-orphan"
    )
    fingerprint = relationship(
        "IncidentFingerprint",
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    platform_detection = relationship(
        "PlatformDetectionResult",
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    archive_audit = relationship(
        "ArchiveExtractionAudit",
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    conversation_turns = relationship(
        "ConversationTurn", back_populates="job", cascade="all, delete-orphan"
    )
    tickets = relationship(
        "Ticket", back_populates="job", cascade="all, delete-orphan"
    )
    telemetry_events = relationship(
        "UploadTelemetryEventRecord",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_user_id_status", "user_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'pending', 'running', 'completed', 'failed', 'cancelled')",
            name="valid_job_status",
        ),
    )

    @validates("status")
    def validate_status(self, _key, value: str) -> str:
        allowed = {"draft", "pending", "running", "completed", "failed", "cancelled"}
        if value not in allowed:
            raise ValueError(f"Invalid status: {value}")
        return value

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return float(delta.total_seconds())
        return None

    @property
    def is_completed(self) -> bool:
        return self.status in {"completed", "failed", "cancelled"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "status": self.status,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "model_config": self.model_config,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "input_manifest": self.input_manifest,
            "result_data": self.result_data,
            "outputs": self.outputs,
            "ticketing": self.ticketing,
            "source": self.source,
            "error_message": self.error_message,
        }


class JobEvent(Base):
    """Event stream for job lifecycle."""

    __tablename__ = "job_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(50), nullable=False)  # Index defined in __table_args__
    data = Column(JSON)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="events")

    __table_args__ = (
        Index("ix_job_events_job_id_created_at", "job_id", "created_at"),
        Index("ix_job_events_event_type", "event_type"),
    )

    @validates("event_type")
    def validate_event(self, _key, value: str) -> str:
        if not value:
            raise ValueError("event_type must not be empty")
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "event_type": self.event_type,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class File(Base):
    """Uploaded artefact linked to a job."""

    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(1024), nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(128), nullable=False)
    _metadata = Column("metadata", JSON, default=dict)

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self.metadata = metadata

    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True))
    processing_error = Column(Text)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="files")
    telemetry_events = relationship(
        "UploadTelemetryEventRecord",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_files_job_id_created_at", "job_id", "created_at"),
        Index("ix_files_checksum", "checksum"),
        CheckConstraint("file_size > 0", name="positive_file_size"),
    )

    @property
    def is_valid(self) -> bool:
        return (not self.processed) and self.processing_error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "processed": self.processed,
            "processing_error": self.processing_error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat()
            if self.processed_at
            else None,
        }


class UploadTelemetryEventRecord(Base):
    """ORM mapping for upload telemetry events."""

    __tablename__ = "upload_telemetry_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(String(32), nullable=False)
    feature_flags = Column(JSONB, nullable=False, default=list)
    status = Column(String(16), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    _metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self.metadata = metadata

    job = relationship("Job", back_populates="telemetry_events")
    file = relationship("File", back_populates="telemetry_events")

    __table_args__ = (
        CheckConstraint(
            "duration_ms >= 0",
            name="ck_upload_telemetry_events_duration_non_negative",
        ),
        Index(
            "ix_upload_telemetry_events_tenant_stage_status_created_at",
            "tenant_id",
            "stage",
            "status",
            "created_at",
        ),
        Index(
            "ix_upload_telemetry_events_upload_stage",
            "upload_id",
            "stage",
        ),
    )

    @validates("duration_ms")
    def _validate_duration_ms(self, _key, value: int) -> int:
        if value is None or value < 0:
            raise ValueError("duration_ms must be greater than or equal to zero")
        return int(value)

    @validates("started_at")
    def _validate_started_at(self, _key, value):
        if value is None:
            raise ValueError("started_at must be provided")
        completed = getattr(self, "completed_at", None)
        if completed is not None and completed < value:
            raise ValueError("started_at cannot be after completed_at")
        return value

    @validates("completed_at")
    def _validate_completed_at(self, _key, value):
        if value is None:
            raise ValueError("completed_at must be provided")
        started = getattr(self, "started_at", None)
        if started is not None and value < started:
            raise ValueError("completed_at cannot be earlier than started_at")
        return value



class Document(Base):
    """Text chunks derived from files, optionally embedded."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    file_id = Column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=True
    )

    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default="text")
    content_embedding = Column(Vector(settings.VECTOR_DIMENSION))
    _metadata = Column("metadata", JSON)
    chunk_index = Column(Integer, default=0)
    chunk_size = Column(Integer)

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self._metadata = metadata

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="documents")
    file = relationship("File")

    __table_args__ = (
        Index("ix_documents_job_id", "job_id"),
        Index("ix_documents_file_id", "file_id"),
        Index(
            "ix_documents_content_embedding_ivfflat",
            "content_embedding",
            postgresql_using="ivfflat",
        ),
    )

    @property
    def has_embedding(self) -> bool:
        return self.content_embedding is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "file_id": str(self.file_id) if self.file_id else None,
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "chunk_size": self.chunk_size,
            "has_embedding": self.has_embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IncidentFingerprint(Base):
    """Vector fingerprint for completed RCA sessions."""

    __tablename__ = "incident_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    embedding_vector = Column(Vector(settings.VECTOR_DIMENSION))
    summary_text = Column(Text, nullable=False)
    relevance_threshold = Column(Float, nullable=False, default=0.5)
    visibility_scope = Column(
        Enum(
            "tenant_only",
            "multi_tenant",
            name="visibility_scope_enum",
            create_type=False,
        ),
        nullable=False,
        default="tenant_only",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    fingerprint_status = Column(
        Enum(
            "available",
            "degraded",
            "missing",
            name="fingerprint_status_enum",
            create_type=False,
        ),
        nullable=False,
        default="missing",
    )
    safeguard_notes = Column(JSONB, nullable=False, default=dict)

    job = relationship("Job", back_populates="fingerprint")

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_incident_fingerprints_session"),
        Index(
            "ix_incident_fingerprints_tenant_scope",
            "tenant_id",
            "visibility_scope",
        ),
        Index(
            "ix_incident_fingerprints_status",
            "fingerprint_status",
        ),
        Index("ix_incident_fingerprints_updated_at", "updated_at"),
        Index(
            "ix_incident_fingerprints_embedding_vector_ivfflat",
            "embedding_vector",
            postgresql_using="ivfflat",
        ),
        CheckConstraint(
            "fingerprint_status != 'available' OR embedding_vector IS NOT NULL",
            name="ck_incident_fingerprints_vector_required",
        ),
        CheckConstraint(
            "char_length(summary_text) <= 4096",
            name="ck_incident_fingerprints_summary_length",
        ),
        CheckConstraint(
            "relevance_threshold >= 0 AND relevance_threshold <= 1",
            name="ck_incident_fingerprints_relevance_bounds",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "tenant_id": str(self.tenant_id),
            "summary_text": self.summary_text,
            "relevance_threshold": float(self.relevance_threshold or 0),
            "visibility_scope": self.visibility_scope,
            "fingerprint_status": self.fingerprint_status,
            "safeguard_notes": self.safeguard_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_available(self) -> bool:
        return self.fingerprint_status == "available"


class PlatformDetectionResult(Base):
    """Detected platform metadata and parser outcomes."""

    __tablename__ = "platform_detection_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    detected_platform = Column(
        Enum(
            "blue_prism",
            "uipath",
            "appian",
            "automation_anywhere",
            "pega",
            "unknown",
            name="detected_platform_enum",
            create_type=False,
        ),
        nullable=False,
        default="unknown",
    )
    confidence_score = Column(Numeric(5, 4), nullable=False, default=0)
    detection_method = Column(Text, nullable=False)
    parser_executed = Column(Boolean, nullable=False, default=False)
    parser_version = Column(Text)
    extracted_entities = Column(JSONB, nullable=False, default=list)
    feature_flag_snapshot = Column(JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="platform_detection")

    __table_args__ = (
        UniqueConstraint("job_id", name="uq_platform_detection_results_job"),
        Index("ix_platform_detection_results_job_id", "job_id"),
        Index("ix_platform_detection_results_created_at", "created_at"),
        Index(
            "ix_platform_detection_results_platform",
            "detected_platform",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_platform_detection_confidence_bounds",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "detected_platform": self.detected_platform,
            "confidence_score": float(self.confidence_score or 0),
            "detection_method": self.detection_method,
            "parser_executed": self.parser_executed,
            "parser_version": self.parser_version,
            "extracted_entities": self.extracted_entities,
            "feature_flag_snapshot": self.feature_flag_snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ArchiveExtractionAudit(Base):
    """Audit records for archive extraction safeguards."""

    __tablename__ = "archive_extraction_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    source_filename = Column(Text, nullable=False)
    archive_type = Column(
        Enum(
            "zip",
            "gz",
            "bz2",
            "xz",
            "tar_gz",
            "tar_bz2",
            "tar_xz",
            name="archive_type_enum",
            create_type=False,
        ),
        nullable=False,
    )
    member_count = Column(Integer, nullable=False, default=0)
    compressed_size_bytes = Column(BigInteger, nullable=False)
    estimated_uncompressed_bytes = Column(BigInteger)
    decompression_ratio = Column(Numeric(10, 2))
    guardrail_status = Column(
        Enum(
            "passed",
            "blocked_ratio",
            "blocked_members",
            "timeout",
            "error",
            name="archive_guardrail_status_enum",
            create_type=False,
        ),
        nullable=False,
        default="passed",
    )
    blocked_reason = Column(Text)
    partial_members = Column(JSONB, nullable=False, default=list)
    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True))

    job = relationship("Job", back_populates="archive_audit")

    __table_args__ = (
        UniqueConstraint("job_id", name="uq_archive_extraction_audits_job"),
        Index("ix_archive_extraction_audits_job_id", "job_id"),
        Index(
            "ix_archive_extraction_audits_guardrail_status",
            "guardrail_status",
        ),
        Index("ix_archive_extraction_audits_completed_at", "completed_at"),
        CheckConstraint(
            "member_count >= 0",
            name="ck_archive_audit_member_count_non_negative",
        ),
        CheckConstraint(
            "compressed_size_bytes > 0",
            name="ck_archive_audit_compressed_size_positive",
        ),
        CheckConstraint(
            "decompression_ratio IS NULL OR decompression_ratio >= 0",
            name="ck_archive_audit_ratio_non_negative",
        ),
        CheckConstraint(
            "guardrail_status NOT IN ('blocked_ratio', 'blocked_members', 'error') OR blocked_reason IS NOT NULL",
            name="ck_archive_audit_blocked_reason_required",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "source_filename": self.source_filename,
            "archive_type": self.archive_type,
            "member_count": self.member_count,
            "compressed_size_bytes": int(self.compressed_size_bytes or 0),
            "estimated_uncompressed_bytes": int(
                self.estimated_uncompressed_bytes or 0
            ),
            "decompression_ratio": float(self.decompression_ratio or 0),
            "guardrail_status": self.guardrail_status,
            "blocked_reason": self.blocked_reason,
            "partial_members": self.partial_members,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }

    @property
    def is_blocked(self) -> bool:
        return self.guardrail_status.startswith("blocked") or (
            self.guardrail_status == "timeout"
        )


class AnalystAuditEvent(Base):
    """Audit log capturing cross-workspace related incident views."""

    __tablename__ = "analyst_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analyst_id = Column(UUID(as_uuid=True), nullable=False)
    source_workspace_id = Column(UUID(as_uuid=True), nullable=False)
    related_workspace_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    related_session_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(
        Enum(
            "viewed_related_incident",
            name="analyst_audit_action_enum",
            create_type=False,
        ),
        nullable=False,
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_analyst_audit_events_analyst_timestamp",
            "analyst_id",
            "timestamp",
        ),
        Index(
            "ix_analyst_audit_events_session",
            "session_id",
            "related_session_id",
        ),
        CheckConstraint(
            "source_workspace_id <> related_workspace_id",
            name="ck_analyst_audit_distinct_workspaces",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "analyst_id": str(self.analyst_id),
            "source_workspace_id": str(self.source_workspace_id),
            "related_workspace_id": str(self.related_workspace_id),
            "session_id": str(self.session_id),
            "related_session_id": str(self.related_session_id),
            "action": self.action,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @property
    def is_cross_workspace(self) -> bool:
        return self.source_workspace_id != self.related_workspace_id


class ConversationTurn(Base):
    """LLM prompt/response history for a job."""

    __tablename__ = "conversation_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(32), nullable=False)
    sequence = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    _metadata = Column("metadata", JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self._metadata = metadata

    job = relationship("Job", back_populates="conversation_turns")

    __table_args__ = (
        Index("ix_conversation_turns_job_sequence", "job_id", "sequence"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "role": self.role,
            "sequence": self.sequence,
            "content": self.content,
            "token_count": self.token_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Ticket(Base):
    """Persisted ITSM ticket metadata."""

    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    platform = Column(String(50), nullable=False)
    ticket_id = Column(String(128), nullable=False)
    url = Column(String(512))
    status = Column(String(50), nullable=False, default="pending")
    profile_name = Column(String(100))
    dry_run = Column(Boolean, default=False, nullable=False)
    payload = Column(JSONB)
    _metadata = Column("metadata", JSONB)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # SLA tracking fields
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    time_to_acknowledge = Column(Integer)  # seconds from created_at to acknowledged_at
    time_to_resolve = Column(Integer)  # seconds from created_at to resolved_at

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self._metadata = metadata

    job = relationship("Job", back_populates="tickets")

    __table_args__ = (
        Index("ix_tickets_job_platform", "job_id", "platform"),
        Index("ix_tickets_ticket_id", "ticket_id"),
        CheckConstraint(
            "platform IN ('servicenow', 'jira')",
            name="valid_ticket_platform",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "platform": self.platform,
            "ticket_id": self.ticket_id,
            "url": self.url,
            "status": self.status,
            "profile_name": self.profile_name,
            "dry_run": self.dry_run,
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "time_to_acknowledge": self.time_to_acknowledge,
            "time_to_resolve": self.time_to_resolve,
        }


class ItsmProfile(Base):
    """Reusable ITSM credential/profile configuration."""

    __tablename__ = "itsm_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    platform = Column(String(50), nullable=False)
    base_url = Column(String(512), nullable=False)
    auth_method = Column(String(50), nullable=False)
    secret_ref = Column(String(255), nullable=False)
    defaults = Column(JSONB)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "platform IN ('servicenow', 'jira')",
            name="valid_itsm_profile_platform",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "platform": self.platform,
            "base_url": self.base_url,
            "auth_method": self.auth_method,
            "secret_ref": self.secret_ref,
            "defaults": self.defaults,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TicketIntegrationSettings(Base):
    """Feature toggle state for ITSM integrations."""

    __tablename__ = "ticket_integration_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    servicenow_enabled = Column(Boolean, default=False, nullable=False)
    jira_enabled = Column(Boolean, default=False, nullable=False)
    dual_mode = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "servicenow_enabled": self.servicenow_enabled,
            "jira_enabled": self.jira_enabled,
            "dual_mode": self.dual_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WatcherConfig(Base):
    """File watcher configuration (single row)."""

    __tablename__ = "watcher_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enabled = Column(Boolean, default=True, nullable=False)
    roots = Column(ARRAY(Text))
    include_globs = Column(ARRAY(Text))
    exclude_globs = Column(ARRAY(Text))
    max_file_size_mb = Column(Integer)
    allowed_mime_types = Column(ARRAY(Text))
    batch_window_seconds = Column(Integer)
    auto_create_jobs = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    events = relationship(
        "WatcherEvent", back_populates="watcher", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_watcher_configs_enabled", "enabled"),)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "enabled": self.enabled,
            "roots": list(self.roots or []),
            "include_globs": list(self.include_globs or []),
            "exclude_globs": list(self.exclude_globs or []),
            "max_file_size_mb": self.max_file_size_mb,
            "allowed_mime_types": list(self.allowed_mime_types or []),
            "batch_window_seconds": self.batch_window_seconds,
            "auto_create_jobs": self.auto_create_jobs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WatcherEvent(Base):
    """Watcher event stream for SSE/broadcasting."""

    __tablename__ = "watcher_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    watcher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("watcher_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    watcher = relationship("WatcherConfig", back_populates="events")

    __table_args__ = (
        Index("ix_watcher_events_event_type", "event_type"),
        Index("ix_watcher_events_created_at", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "watcher_id": str(self.watcher_id) if self.watcher_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """User accounts for authentication."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)  # Index defined in __table_args__
    email = Column(String(255), unique=True, nullable=False)  # Index defined in __table_args__
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Index defined in __table_args__
    is_superuser = Column(Boolean, default=False, nullable=False)
    full_name = Column(String(255))
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat()
            if self.last_login_at
            else None,
        }


def _metadata_getter(instance):
    return getattr(instance, "_metadata", None)


def _metadata_setter(instance, value):
    if isinstance(instance, UploadTelemetryEventRecord):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            raise ValueError("UploadTelemetryEventRecord.metadata must be a dictionary")
    setattr(instance, "_metadata", value)


File.metadata = property(_metadata_getter, _metadata_setter)
Document.metadata = property(_metadata_getter, _metadata_setter)
ConversationTurn.metadata = property(_metadata_getter, _metadata_setter)
Ticket.metadata = property(_metadata_getter, _metadata_setter)
UploadTelemetryEventRecord.metadata = property(_metadata_getter, _metadata_setter)
