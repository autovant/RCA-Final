"""Shared file-processing models for archive auditing and platform signals."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

__all__ = [
    "ArchiveType",
    "GuardrailStatus",
    "ArchiveExtractionSummary",
    "PartialMember",
]


class ArchiveType(str, Enum):
    """Supported archive container types."""

    ZIP = "zip"
    GZ = "gz"
    BZ2 = "bz2"
    XZ = "xz"
    TAR_GZ = "tar_gz"
    TAR_BZ2 = "tar_bz2"
    TAR_XZ = "tar_xz"


class GuardrailStatus(str, Enum):
    """Outcome of archive safeguard evaluation."""

    PASSED = "passed"
    BLOCKED_RATIO = "blocked_ratio"
    BLOCKED_MEMBERS = "blocked_members"
    TIMEOUT = "timeout"
    ERROR = "error"


class PartialMember(BaseModel):
    """Describes an archive member that triggered guardrails."""

    path: str
    reason: str
    size_bytes: Optional[int] = None


class ArchiveExtractionSummary(BaseModel):
    """API-safe representation of `ArchiveExtractionAudit`."""

    job_id: str
    source_filename: str
    archive_type: ArchiveType
    member_count: int = Field(ge=0)
    compressed_size_bytes: int = Field(ge=0)
    estimated_uncompressed_bytes: Optional[int] = Field(default=None, ge=0)
    decompression_ratio: Optional[float] = Field(default=None, ge=0.0)
    guardrail_status: GuardrailStatus = GuardrailStatus.PASSED
    blocked_reason: Optional[str] = None
    partial_members: List[PartialMember] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_blocked(self) -> bool:
        return self.guardrail_status not in {GuardrailStatus.PASSED}
