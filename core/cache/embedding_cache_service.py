"""Embedding cache service primitives and ORM models."""

from __future__ import annotations

import base64
import binascii
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple, cast

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from core.db.models import Base
from core.config import settings
from core.metrics.pipeline_metrics import PipelineMetricsCollector

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover - optional dependency during tests
    AESGCM = None  # type: ignore[assignment]

_SCRUB_CONFIRMATION_KEYS = ("pii_scrubbed", "scrubbed", "scrubbed_confirmed")


class EmbeddingCacheEntry(Base):
    """SQLAlchemy model for cached embeddings."""

    __tablename__ = "embedding_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content_sha256 = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    embedding_vector_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hit_count = Column(BigInteger, nullable=False, default=0)
    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    payload_ciphertext = Column(LargeBinary, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "content_sha256",
            "model",
            name="uq_embedding_cache_tenant_sha_model",
        ),
        Index("ix_embedding_cache_last_accessed_at", "last_accessed_at"),
        CheckConstraint(
            "char_length(content_sha256) = 64",
            name="ck_embedding_cache_sha_length",
        ),
        CheckConstraint(
            "hit_count >= 0",
            name="ck_embedding_cache_hit_count_non_negative",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_embedding_cache_expiry_after_creation",
        ),
    )

    @validates("content_sha256")
    def _validate_sha256(self, _key: str, value: str) -> str:
        if not value or len(value) != 64:
            raise ValueError(
                "content_sha256 must be a 64-character SHA-256 hex digest"
            )
        return value.lower()

    @validates("hit_count")
    def _validate_hit_count(self, _key: str, value: int) -> int:
        if value is None or value < 0:
            raise ValueError("hit_count must be non-negative")
        return int(value)

    @validates("expires_at")
    def _validate_expires_at(
        self, _key: str, value: Optional[datetime]
    ) -> Optional[datetime]:
        created_at = getattr(self, "created_at", None)
        if value is not None and created_at is not None and value <= created_at:
            raise ValueError("expires_at must be after created_at when provided")
        return value


@dataclass
class EmbeddingCacheHit:
    """Result payload returned when the cache resolves a lookup."""

    entry: EmbeddingCacheEntry
    embedding: List[float]


class EmbeddingCacheService:
    """High-level API for interacting with the embedding cache."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        metrics: Optional[PipelineMetricsCollector] = None,
    ) -> None:
        self._session = session
        self._metrics = metrics
        encryption_config = settings.embedding_cache_encryption
        key_b64 = encryption_config.KEY if encryption_config else None
        self._aesgcm: Optional[Any] = None
        if encryption_config and encryption_config.ENABLED:
            if AESGCM is None:
                raise RuntimeError(
                    "cryptography package is required when embedding cache encryption is enabled"
                )
            if not key_b64:
                raise ValueError(
                    "EMBEDDING_CACHE_ENCRYPTION_KEY must be configured when encryption is enabled"
                )
            try:
                key = base64.b64decode(key_b64)
            except binascii.Error as exc:  # pragma: no cover - validated in settings
                raise ValueError(
                    "EMBEDDING_CACHE_ENCRYPTION_KEY must be valid base64"
                ) from exc

            if len(key) != 32:
                raise ValueError(
                    "EMBEDDING_CACHE_ENCRYPTION_KEY must decode to 32 bytes"
                )

            self._aesgcm = AESGCM(key)

    async def lookup(
        self, tenant_id: uuid.UUID, content_hash: str, model: str
    ) -> Optional[EmbeddingCacheHit]:
        """Fetch a cached embedding entry if available."""

        stmt = (
            select(EmbeddingCacheEntry)
            .where(EmbeddingCacheEntry.tenant_id == tenant_id)
            .where(EmbeddingCacheEntry.content_sha256 == content_hash.lower())
            .where(EmbeddingCacheEntry.model == model)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        entry = result.scalar_one_or_none()

        if self._metrics:
            self._metrics.record_cache_request(
                tenant_id=str(tenant_id),
                model=model,
                hit=entry is not None,
            )

        if not entry:
            return None

        entry_obj = cast(EmbeddingCacheEntry, entry)
        current_hits = int(getattr(entry_obj, "hit_count", 0) or 0)
        setattr(entry_obj, "hit_count", current_hits + 1)
        setattr(entry_obj, "last_accessed_at", datetime.now(timezone.utc))
        await self._session.flush()

        payload_value = getattr(entry_obj, "payload_ciphertext")
        if isinstance(payload_value, memoryview):  # pragma: no cover - defensive
            payload_value = payload_value.tobytes()
        if not isinstance(payload_value, (bytes, bytearray)):
            raise ValueError("Cached embedding payload must be binary data")

        payload_bytes = bytes(payload_value)
        embedding = self._decrypt_payload(payload_bytes)

        return EmbeddingCacheHit(entry=entry_obj, embedding=embedding)

    async def store(
        self,
        tenant_id: uuid.UUID,
        content_hash: str,
        model: str,
        embedding_vector_id: Optional[uuid.UUID],
        *,
        expires_at: Optional[datetime] = None,
        scrub_metadata: Optional[Mapping[str, object]] = None,
        embedding: Sequence[float],
    ) -> EmbeddingCacheEntry:
        """Persist a new embedding cache entry."""

        self._validate_scrub_confirmation(scrub_metadata)
        payload_ciphertext = self._encrypt_payload(embedding)

        entry = EmbeddingCacheEntry(
            tenant_id=tenant_id,
            content_sha256=content_hash.lower(),
            model=model,
            embedding_vector_id=embedding_vector_id,
            expires_at=expires_at,
            payload_ciphertext=payload_ciphertext,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def select_stale_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        older_than: datetime,
        limit: int,
    ) -> List[Tuple[uuid.UUID, str]]:
        """Fetch identifiers for cache entries eligible for eviction."""

        batch_size = max(1, int(limit))
        stmt = (
            select(EmbeddingCacheEntry.id, EmbeddingCacheEntry.model)
            .where(EmbeddingCacheEntry.tenant_id == tenant_id)
            .where(EmbeddingCacheEntry.hit_count == 0)
            .where(EmbeddingCacheEntry.created_at <= older_than)
            .order_by(EmbeddingCacheEntry.created_at.asc())
            .limit(batch_size)
        )
        result = await self._session.execute(stmt)
        records = result.all()
        resolved: List[Tuple[uuid.UUID, str]] = []
        for entry_id, model in records:
            resolved.append((cast(uuid.UUID, entry_id), cast(str, model or "unknown")))
        return resolved

    async def delete_entries(
        self,
        entry_ids: Iterable[uuid.UUID],
    ) -> List[str]:
        """Delete cache entries by identifier returning their model labels."""

        identifiers = [uuid.UUID(str(item)) for item in entry_ids]
        if not identifiers:
            return []

        stmt = (
            delete(EmbeddingCacheEntry)
            .where(EmbeddingCacheEntry.id.in_(identifiers))
            .returning(EmbeddingCacheEntry.model)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        models = [cast(str, row[0] or "unknown") for row in result.fetchall()]
        return models

    @staticmethod
    def _validate_scrub_confirmation(
        metadata: Optional[Mapping[str, object]]
    ) -> None:
        if not metadata:
            raise ValueError(
                "Embedding cache writes require scrub confirmation metadata"
            )

        for key in _SCRUB_CONFIRMATION_KEYS:
            value = metadata.get(key)
            if isinstance(value, bool) and value:
                return

        privacy = metadata.get("privacy")
        if isinstance(privacy, Mapping):
            for key in _SCRUB_CONFIRMATION_KEYS:
                value = privacy.get(key)
                if isinstance(value, bool) and value:
                    return

        raise ValueError(
            "Embedding cache writes require metadata confirming PII scrubbing"
        )

    def _encrypt_payload(self, embedding: Sequence[float]) -> bytes:
        serialized = json.dumps(list(embedding), separators=(",", ":")).encode("utf-8")
        if not self._aesgcm:
            return serialized

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, serialized, None)
        return nonce + ciphertext

    def _decrypt_payload(self, payload: bytes) -> List[float]:
        if not self._aesgcm:
            decoded = payload.decode("utf-8")
        else:
            nonce = payload[:12]
            ciphertext = payload[12:]
            decoded = self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

        values = json.loads(decoded)
        if not isinstance(values, list):
            raise ValueError("Cached embedding payload must decode to a list of floats")
        return [float(item) for item in values]
