"""
Database models for the RCA Engine.
Includes job orchestration primitives, conversation traceability, ticket
metadata, and watcher configuration as outlined in the PRD.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
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
    conversation_turns = relationship(
        "ConversationTurn", back_populates="job", cascade="all, delete-orphan"
    )
    tickets = relationship(
        "Ticket", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_user_id_status", "user_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="valid_job_status",
        ),
    )

    @validates("status")
    def validate_status(self, _key, value: str) -> str:
        allowed = {"pending", "running", "completed", "failed", "cancelled"}
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
    event_type = Column(String(50), nullable=False, index=True)
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
    checksum = Column(String(128), nullable=False, unique=True)
    _metadata = Column("metadata", JSON, default=dict)

    def __init__(self, *args, **kwargs):
        metadata = kwargs.pop("metadata", None)
        super().__init__(*args, **kwargs)
        if metadata is not None:
            self._metadata = metadata

    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True))
    processing_error = Column(Text)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="files")

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
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
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
    setattr(instance, "_metadata", value)


File.metadata = property(_metadata_getter, _metadata_setter)
Document.metadata = property(_metadata_getter, _metadata_setter)
ConversationTurn.metadata = property(_metadata_getter, _metadata_setter)
Ticket.metadata = property(_metadata_getter, _metadata_setter)
