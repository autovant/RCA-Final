"""Archive safeguard validators for decompression abuse prevention."""

from __future__ import annotations

import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

__all__ = [
    "SafeguardViolation",
    "SafeguardConfig",
    "evaluate_archive_safeguards",
]

# Default thresholds to prevent decompression bombs
DEFAULT_MAX_DECOMPRESSION_RATIO = 100  # Max ratio of uncompressed:compressed size
DEFAULT_MAX_MEMBER_COUNT = 10000  # Max number of files in archive
DEFAULT_MIN_COMPRESSED_SIZE = 1024  # Minimum compressed size to check ratio (1KB)


@dataclass
class SafeguardViolation:
    """Represents a safeguard violation detected during archive inspection."""

    code: str
    message: str
    detail: Optional[str] = None
    severity: str = "error"  # error, warning


@dataclass
class SafeguardConfig:
    """Configuration for archive safeguard checks."""

    max_decompression_ratio: float = DEFAULT_MAX_DECOMPRESSION_RATIO
    max_member_count: int = DEFAULT_MAX_MEMBER_COUNT
    min_compressed_size_for_ratio_check: int = DEFAULT_MIN_COMPRESSED_SIZE


def evaluate_archive_safeguards(
    archive_path: Path,
    *,
    config: Optional[SafeguardConfig] = None,
) -> List[SafeguardViolation]:
    """Evaluate archive against safeguard thresholds before extraction.
    
    Checks for:
    - Decompression ratio (potential decompression bomb)
    - Member count (potential zip bomb)
    - Path traversal attempts (basic check)
    
    Args:
        archive_path: Path to the archive file
        config: Safeguard configuration (uses defaults if None)
    
    Returns:
        List of violations detected (empty if safe)
    """
    config = config or SafeguardConfig()
    violations: List[SafeguardViolation] = []

    suffix = archive_path.suffix.lower()
    
    try:
        if suffix == ".zip":
            violations.extend(_check_zip_safeguards(archive_path, config))
        elif suffix in (".tar", ".tgz", ".tbz2", ".txz") or (
            suffix in (".gz", ".bz2", ".xz") and archive_path.stem.endswith(".tar")
        ):
            violations.extend(_check_tar_safeguards(archive_path, config))
        # Note: Single-file compression (.gz, .bz2, .xz without .tar) has limited risk
        # as they decompress to a single file, so we skip safeguard checks for those
    except Exception as e:
        violations.append(
            SafeguardViolation(
                code="inspection_failed",
                message="Failed to inspect archive for safeguards",
                detail=str(e),
                severity="warning",
            )
        )

    return violations


def _check_zip_safeguards(
    archive_path: Path,
    config: SafeguardConfig,
) -> List[SafeguardViolation]:
    """Check ZIP archive for decompression bombs and excessive members."""
    violations: List[SafeguardViolation] = []

    with zipfile.ZipFile(archive_path) as zf:
        compressed_size = archive_path.stat().st_size
        uncompressed_size = sum(info.file_size for info in zf.infolist())
        member_count = len(zf.infolist())

        # Check member count
        if member_count > config.max_member_count:
            violations.append(
                SafeguardViolation(
                    code="excessive_member_count",
                    message=f"Archive contains too many members ({member_count})",
                    detail=f"limit={config.max_member_count}",
                )
            )

        # Check decompression ratio (only if compressed size is meaningful)
        if compressed_size >= config.min_compressed_size_for_ratio_check:
            ratio = uncompressed_size / compressed_size if compressed_size > 0 else 0
            if ratio > config.max_decompression_ratio:
                violations.append(
                    SafeguardViolation(
                        code="excessive_decompression_ratio",
                        message=f"Decompression ratio too high ({ratio:.1f}:1)",
                        detail=f"compressed={compressed_size} uncompressed={uncompressed_size} limit={config.max_decompression_ratio}",
                    )
                )

        # Check for path traversal attempts
        for info in zf.infolist():
            if ".." in info.filename or info.filename.startswith("/"):
                violations.append(
                    SafeguardViolation(
                        code="path_traversal_attempt",
                        message=f"Archive member attempts path traversal: {info.filename}",
                        severity="error",
                    )
                )

    return violations


def _check_tar_safeguards(
    archive_path: Path,
    config: SafeguardConfig,
) -> List[SafeguardViolation]:
    """Check TAR archive (with optional compression) for safeguards."""
    violations: List[SafeguardViolation] = []

    # Determine tar mode based on file extension
    suffix = archive_path.suffix.lower()
    if suffix == ".tgz" or (suffix == ".gz" and archive_path.stem.endswith(".tar")):
        mode = "r:gz"
    elif suffix == ".tbz2" or (suffix == ".bz2" and archive_path.stem.endswith(".tar")):
        mode = "r:bz2"
    elif suffix == ".txz" or (suffix == ".xz" and archive_path.stem.endswith(".tar")):
        mode = "r:xz"
    else:
        mode = "r"

    with tarfile.open(str(archive_path), mode) as tar:
        compressed_size = archive_path.stat().st_size
        members = tar.getmembers()
        member_count = len(members)
        uncompressed_size = sum(m.size for m in members if m.isfile())

        # Check member count
        if member_count > config.max_member_count:
            violations.append(
                SafeguardViolation(
                    code="excessive_member_count",
                    message=f"Archive contains too many members ({member_count})",
                    detail=f"limit={config.max_member_count}",
                )
            )

        # Check decompression ratio
        if compressed_size >= config.min_compressed_size_for_ratio_check:
            ratio = uncompressed_size / compressed_size if compressed_size > 0 else 0
            if ratio > config.max_decompression_ratio:
                violations.append(
                    SafeguardViolation(
                        code="excessive_decompression_ratio",
                        message=f"Decompression ratio too high ({ratio:.1f}:1)",
                        detail=f"compressed={compressed_size} uncompressed={uncompressed_size} limit={config.max_decompression_ratio}",
                    )
                )

        # Check for path traversal attempts
        for member in members:
            if ".." in member.name or member.name.startswith("/"):
                violations.append(
                    SafeguardViolation(
                        code="path_traversal_attempt",
                        message=f"Archive member attempts path traversal: {member.name}",
                        severity="error",
                    )
                )
            # Check for absolute paths or attempts to escape
            if member.name.startswith("/") or member.name.startswith("../"):
                violations.append(
                    SafeguardViolation(
                        code="absolute_path_detected",
                        message=f"Archive member uses absolute or parent path: {member.name}",
                        severity="warning",
                    )
                )

    return violations
