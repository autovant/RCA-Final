"""Archive extraction utilities for compressed uploads."""

from __future__ import annotations

import bz2
import gzip
import lzma
import shutil
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO, List, Optional

__all__ = [
    "ArchiveExtractionError",
    "ExtractionTimeoutExceeded",
    "ExtractionSizeLimitExceeded",
    "UnsupportedArchiveTypeError",
    "ExtractedFile",
    "ExtractionResult",
    "ArchiveExtractor",
]

DEFAULT_SIZE_LIMIT_BYTES = 100 * 1024 * 1024  # 100 MiB
DEFAULT_TIMEOUT_SECONDS = 30
_CHUNK_SIZE = 64 * 1024


class ArchiveExtractionError(Exception):
    """Base exception for archive extraction failures."""


class ExtractionTimeoutExceeded(ArchiveExtractionError):
    """Raised when extraction exceeds the configured timeout."""


class ExtractionSizeLimitExceeded(ArchiveExtractionError):
    """Raised when extraction exceeds the configured cumulative size limit."""


class UnsupportedArchiveTypeError(ArchiveExtractionError):
    """Raised when attempting to extract an unsupported archive format."""


@dataclass
class ExtractedFile:
    """Metadata about a single extracted file."""

    path: Path
    original_path: str
    size_bytes: int


@dataclass
class ExtractionResult:
    """Return value for archive extraction requests."""

    destination: Path
    files: List[ExtractedFile]
    total_size_bytes: int
    duration_seconds: float
    warnings: List[str]
    _owns_destination: bool = True

    def cleanup(self) -> None:
        """Remove the extraction directory when owned by this result."""
        if self._owns_destination and self.destination.exists():
            shutil.rmtree(self.destination, ignore_errors=True)


class ArchiveExtractor:
    """Extract archives with size and timeout guardrails.
    
    Supported formats:
    - .gz (gzip)
    - .bz2 (bzip2)
    - .xz (lzma)
    - .zip (zip)
    - .tar, .tar.gz, .tgz (tar + gzip)
    - .tar.bz2, .tbz2 (tar + bzip2)
    - .tar.xz, .txz (tar + lzma)
    """

    def __init__(
        self,
        *,
        size_limit_bytes: int = DEFAULT_SIZE_LIMIT_BYTES,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if size_limit_bytes <= 0:
            raise ValueError("size_limit_bytes must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._size_limit_bytes = size_limit_bytes
        self._timeout_seconds = timeout_seconds

    def extract(self, archive_path: Path, *, destination: Optional[Path] = None) -> ExtractionResult:
        start = time.perf_counter()
        archive_path = archive_path.resolve()
        if not archive_path.exists():
            raise ArchiveExtractionError(f"Archive not found: {archive_path}")

        suffix = archive_path.suffix.lower()
        temp_dir_created = False
        if destination is None:
            destination = Path(tempfile.mkdtemp(prefix="rca_extract_"))
            temp_dir_created = True
        else:
            destination.mkdir(parents=True, exist_ok=True)

        files: List[ExtractedFile] = []
        warnings: List[str] = []
        total_size = 0

        try:
            # Determine archive type and extract
            if suffix == ".gz":
                # Check if it's a tar.gz
                if archive_path.stem.endswith(".tar"):
                    total_size, files, warnings = self._extract_tar(archive_path, destination, start, "gz")
                else:
                    total_size, files = self._extract_gzip(archive_path, destination, start)
                    warnings = []
            elif suffix == ".bz2":
                # Check if it's a tar.bz2
                if archive_path.stem.endswith(".tar"):
                    total_size, files, warnings = self._extract_tar(archive_path, destination, start, "bz2")
                else:
                    total_size, files = self._extract_bzip2(archive_path, destination, start)
                    warnings = []
            elif suffix == ".xz":
                # Check if it's a tar.xz
                if archive_path.stem.endswith(".tar"):
                    total_size, files, warnings = self._extract_tar(archive_path, destination, start, "xz")
                else:
                    total_size, files = self._extract_xz(archive_path, destination, start)
                    warnings = []
            elif suffix in (".tgz", ".tbz2", ".txz"):
                # Shorthand tar formats
                compression = {"tgz": "gz", "tbz2": "bz2", "txz": "xz"}[suffix[1:]]
                total_size, files, warnings = self._extract_tar(archive_path, destination, start, compression)
            elif suffix == ".tar":
                total_size, files, warnings = self._extract_tar(archive_path, destination, start, None)
            elif suffix == ".zip":
                total_size, files, warnings = self._extract_zip(archive_path, destination, start)
            else:
                raise UnsupportedArchiveTypeError(f"Unsupported archive type: {archive_path.suffix}")

            duration = time.perf_counter() - start
            return ExtractionResult(
                destination=destination,
                files=files,
                total_size_bytes=total_size,
                duration_seconds=duration,
                warnings=warnings,
                _owns_destination=temp_dir_created,
            )
        except Exception:
            if temp_dir_created:
                shutil.rmtree(destination, ignore_errors=True)
            raise

    # Internal helpers -------------------------------------------------

    def _ensure_within_limits(self, total_size: int, start: float) -> None:
        if total_size > self._size_limit_bytes:
            raise ExtractionSizeLimitExceeded(
                f"Archive exceeded size limit of {self._size_limit_bytes} bytes"
            )
        if time.perf_counter() - start > self._timeout_seconds:
            raise ExtractionTimeoutExceeded(
                f"Archive extraction exceeded timeout of {self._timeout_seconds} seconds"
            )

    def _extract_gzip(
        self,
        archive_path: Path,
        destination: Path,
        start: float,
    ) -> tuple[int, List[ExtractedFile]]:
        output_name = archive_path.stem or "extracted"
        output_path = destination / output_name

        total_size = 0
        with gzip.open(archive_path, "rb") as src, output_path.open("wb") as dest:
            for chunk in iter(lambda: src.read(_CHUNK_SIZE), b""):
                total_size += len(chunk)
                self._ensure_within_limits(total_size, start)
                dest.write(chunk)

        return total_size, [ExtractedFile(path=output_path, original_path=output_name, size_bytes=total_size)]

    def _extract_zip(
        self,
        archive_path: Path,
        destination: Path,
        start: float,
    ) -> tuple[int, List[ExtractedFile], List[str]]:
        files: List[ExtractedFile] = []
        warnings: List[str] = []
        total_size = 0

        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                safe_path = self._resolve_member_path(destination, member.filename)
                safe_path.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(member, "r") as src, safe_path.open("wb") as dest:
                    copied = self._copy_stream(src, dest, start, total_size)
                    total_size += copied
                    self._ensure_within_limits(total_size, start)

                files.append(
                    ExtractedFile(
                        path=safe_path,
                        original_path=member.filename,
                        size_bytes=copied,
                    )
                )

            if not files:
                warnings.append("Archive did not contain any files")

        return total_size, files, warnings

    def _copy_stream(
        self,
    src: IO[bytes],
    dest: IO[bytes],
        start: float,
        total_size: int,
    ) -> int:
        copied = 0
        for chunk in iter(lambda: src.read(_CHUNK_SIZE), b""):
            copied += len(chunk)
            self._ensure_within_limits(total_size + copied, start)
            dest.write(chunk)
        return copied

    def _resolve_member_path(self, destination: Path, member_name: str) -> Path:
        # Prevent zip-slip by resolving the target path inside the destination.
        sanitized = Path(member_name).as_posix()
        sanitized = sanitized.lstrip("/")
        target = destination / sanitized
        target_resolved = target.resolve()
        destination_resolved = destination.resolve()
        if not str(target_resolved).startswith(str(destination_resolved)):
            raise ArchiveExtractionError(
                f"Archive member escapes extraction directory: {member_name}"
            )
        return target_resolved

    def _extract_bzip2(
        self,
        archive_path: Path,
        destination: Path,
        start: float,
    ) -> tuple[int, List[ExtractedFile]]:
        """Extract a bzip2 compressed file."""
        output_name = archive_path.stem or "extracted"
        output_path = destination / output_name

        total_size = 0
        with bz2.open(archive_path, "rb") as src, output_path.open("wb") as dest:
            for chunk in iter(lambda: src.read(_CHUNK_SIZE), b""):
                total_size += len(chunk)
                self._ensure_within_limits(total_size, start)
                dest.write(chunk)

        return total_size, [ExtractedFile(path=output_path, original_path=output_name, size_bytes=total_size)]

    def _extract_xz(
        self,
        archive_path: Path,
        destination: Path,
        start: float,
    ) -> tuple[int, List[ExtractedFile]]:
        """Extract an XZ/LZMA compressed file."""
        output_name = archive_path.stem or "extracted"
        output_path = destination / output_name

        total_size = 0
        with lzma.open(archive_path, "rb") as src, output_path.open("wb") as dest:
            for chunk in iter(lambda: src.read(_CHUNK_SIZE), b""):
                total_size += len(chunk)
                self._ensure_within_limits(total_size, start)
                dest.write(chunk)

        return total_size, [ExtractedFile(path=output_path, original_path=output_name, size_bytes=total_size)]

    def _extract_tar(
        self,
        archive_path: Path,
        destination: Path,
        start: float,
        compression: Optional[str] = None,
    ) -> tuple[int, List[ExtractedFile], List[str]]:
        """Extract a tar archive with optional compression (gz, bz2, xz).
        
        Args:
            archive_path: Path to the tar archive
            destination: Extraction destination directory
            start: Start time for timeout checks
            compression: Compression type ('gz', 'bz2', 'xz') or None for uncompressed
        """
        files: List[ExtractedFile] = []
        warnings: List[str] = []
        total_size = 0

        # Determine tar mode
        if compression == "gz":
            mode = "r:gz"
        elif compression == "bz2":
            mode = "r:bz2"
        elif compression == "xz":
            mode = "r:xz"
        else:
            mode = "r"

        with tarfile.open(str(archive_path), mode) as tar:
            for member in tar.getmembers():
                # Skip directories and special files
                if not member.isfile():
                    continue

                # Prevent tar-slip attacks
                safe_path = self._resolve_member_path(destination, member.name)
                safe_path.parent.mkdir(parents=True, exist_ok=True)

                # Extract member with streaming to enforce limits
                file_obj = tar.extractfile(member)
                if file_obj is None:
                    continue

                try:
                    with file_obj, safe_path.open("wb") as dest:
                        copied = self._copy_stream(file_obj, dest, start, total_size)
                        total_size += copied
                        self._ensure_within_limits(total_size, start)

                    files.append(
                        ExtractedFile(
                            path=safe_path,
                            original_path=member.name,
                            size_bytes=copied,
                        )
                    )
                finally:
                    file_obj.close()

            if not files:
                warnings.append("Archive did not contain any files")

        return total_size, files, warnings
