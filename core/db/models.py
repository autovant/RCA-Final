"""
Database models for RCA Engine.
SQLAlchemy models with pgvector support for embeddings.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, DateTime, Integer, Boolean, Text, 
    ForeignKey, JSON, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Job(Base):
    """Job model for RCA analysis tasks."""
    
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # User information
    user_id = Column(String(100), nullable=False, index=True)
    
    # Job configuration
    input_manifest = Column(JSON, nullable=False)
    provider = Column(String(50), nullable=False, default="ollama")
    model = Column(String(100), nullable=False, default="llama2")
    
    # Processing metadata
    priority = Column(Integer, default=0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    result_data = Column(JSON)
    error_message = Column(Text)
    
    # Relationships
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")
    files = relationship("File", back_populates="job", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_user_id_status", "user_id", "status"),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')", name="valid_job_status"),
    )
    
    @validates("status")
    def validate_status(self, key, status):
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        return status
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "status": self.status,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "result_data": self.result_data,
            "error_message": self.error_message
        }


class JobEvent(Base):
    """Event model for job lifecycle tracking."""
    
    __tablename__ = "job_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="events")
    
    # Indexes
    __table_args__ = (
        Index("ix_job_events_job_id_created_at", "job_id", "created_at"),
        Index("ix_job_events_event_type", "event_type"),
    )
    
    @validates("event_type")
    def validate_event_type(self, key, event_type):
        valid_types = [
            "created", "queued", "started", "progress", "warning", 
            "needs_input", "retry", "completed", "failed", "cancelled"
        ]
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type: {event_type}")
        return event_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "event_type": self.event_type,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class File(Base):
    """File model for uploaded documents."""
    
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False, unique=True)
    
    # Processing metadata
    processed = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text)
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    job = relationship("Job", back_populates="files")
    
    # Indexes
    __table_args__ = (
        Index("ix_files_job_id", "job_id"),
        Index("ix_files_checksum", "checksum"),
        CheckConstraint("file_size > 0", name="positive_file_size"),
    )
    
    @property
    def is_valid(self) -> bool:
        """Check if file is valid for processing."""
        return self.processed is False and self.processing_error is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
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
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }


class Document(Base):
    """Document model for processed content with embeddings."""
    
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default="text")
    
    # Vector embedding
    content_embedding = Column(Vector(settings.VECTOR_DIMENSION))
    
    # Metadata
    metadata = Column(JSON)
    chunk_index = Column(Integer, default=0)
    chunk_size = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="documents")
    file = relationship("File")
    
    # Indexes
    __table_args__ = (
        Index("ix_documents_job_id", "job_id"),
        Index("ix_documents_file_id", "file_id"),
        Index("ix_documents_content_embedding_ivfflat", "content_embedding", postgresql_using="ivfflat"),
    )
    
    @property
    def has_embedding(self) -> bool:
        """Check if document has embedding."""
        return self.content_embedding is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
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
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile
    full_name = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Indexes
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }


# Import settings for vector dimension
from core.config import settings