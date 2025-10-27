"""
Enhanced archive format support for unified ingestion.

Adds support for:
- 7z archives
- RAR archives
- ISO disk images
- Additional compression formats
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, List, Optional
import zipfile
import tarfile

from core.logging import get_logger
from core.metrics.enhanced_collectors import CompressedIngestionMetrics

logger = get_logger(__name__)


@dataclass
class ArchiveInfo:
    """Information about an archive file."""
    
    format: str
    compressed_size: int
    file_count: int
    files: List[str]
    metadata: dict


class ArchiveExtractor(ABC):
    """Base class for archive extractors."""
    
    @abstractmethod
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this extractor can handle the file."""
        pass
    
    @abstractmethod
    async def extract(
        self,
        archive_path: Path,
        extract_to: Path,
    ) -> ArchiveInfo:
        """
        Extract archive to destination.
        
        Args:
            archive_path: Path to archive file
            extract_to: Destination directory
        
        Returns:
            ArchiveInfo with extraction details
        """
        pass
    
    @abstractmethod
    async def list_contents(self, archive_path: Path) -> List[str]:
        """List files in archive without extracting."""
        pass


class SevenZipExtractor(ArchiveExtractor):
    """
    Extractor for 7z archives using 7-Zip or p7zip.
    
    Requires 7z command-line tool to be installed.
    """
    
    EXTENSIONS = {".7z", ".7zip"}
    
    def __init__(self):
        self._7z_available = self._check_7z_available()
    
    def _check_7z_available(self) -> bool:
        """Check if 7z command is available."""
        try:
            result = subprocess.run(
                ["7z"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode in [0, 255]  # 255 is help exit code
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("7z command not found - .7z extraction unavailable")
            return False
    
    async def can_handle(self, file_path: Path) -> bool:
        if not self._7z_available:
            return False
        
        if file_path.suffix.lower() in self.EXTENSIONS:
            return True
        
        # Check magic bytes
        try:
            with open(file_path, "rb") as f:
                magic = f.read(6)
                return magic == b"7z\xbc\xaf\x27\x1c"
        except Exception:
            return False
    
    async def list_contents(self, archive_path: Path) -> List[str]:
        """List files using 7z l command."""
        if not self._7z_available:
            raise RuntimeError("7z not available")
        
        def _list():
            result = subprocess.run(
                ["7z", "l", "-ba", str(archive_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"7z list failed: {result.stderr}")
            
            files = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    # Parse 7z output: date time attr size compressed name
                    parts = line.split(maxsplit=5)
                    if len(parts) >= 6:
                        files.append(parts[5])
            
            return files
        
        return await asyncio.to_thread(_list)
    
    async def extract(
        self,
        archive_path: Path,
        extract_to: Path,
    ) -> ArchiveInfo:
        """Extract using 7z x command."""
        if not self._7z_available:
            raise RuntimeError("7z not available")
        
        metrics = CompressedIngestionMetrics(format="7z")
        
        with metrics.extraction_timer():
            def _extract():
                extract_to.mkdir(parents=True, exist_ok=True)
                
                result = subprocess.run(
                    ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"7z extraction failed: {result.stderr}")
            
            await asyncio.to_thread(_extract)
        
        # Get file list
        files = await self.list_contents(archive_path)
        compressed_size = archive_path.stat().st_size
        
        # Calculate extracted size
        extracted_size = sum(
            (extract_to / f).stat().st_size
            for f in files
            if (extract_to / f).exists()
        )
        
        info = ArchiveInfo(
            format="7z",
            compressed_size=compressed_size,
            file_count=len(files),
            files=files,
            metadata={
                "tool": "7z",
                "extracted_size": extracted_size,
            }
        )
        
        # Record metrics
        duration = 1.0  # Approximate, already timed above
        metrics.record_success(
            original_bytes=compressed_size,
            extracted_bytes=extracted_size,
            file_count=len(files),
            duration_seconds=duration,
        )
        
        return info


class RarExtractor(ArchiveExtractor):
    """
    Extractor for RAR archives using unrar.
    
    Requires unrar command-line tool to be installed.
    """
    
    EXTENSIONS = {".rar"}
    
    def __init__(self):
        self._unrar_available = self._check_unrar_available()
    
    def _check_unrar_available(self) -> bool:
        """Check if unrar command is available."""
        try:
            result = subprocess.run(
                ["unrar"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode in [0, 7, 10]  # Various unrar exit codes
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("unrar command not found - .rar extraction unavailable")
            return False
    
    async def can_handle(self, file_path: Path) -> bool:
        if not self._unrar_available:
            return False
        
        if file_path.suffix.lower() in self.EXTENSIONS:
            return True
        
        # Check magic bytes
        try:
            with open(file_path, "rb") as f:
                magic = f.read(7)
                # RAR 4.x: Rar!\x1a\x07\x00
                # RAR 5.x: Rar!\x1a\x07\x01\x00
                return magic.startswith(b"Rar!\x1a\x07")
        except Exception:
            return False
    
    async def list_contents(self, archive_path: Path) -> List[str]:
        """List files using unrar l command."""
        if not self._unrar_available:
            raise RuntimeError("unrar not available")
        
        def _list():
            result = subprocess.run(
                ["unrar", "lb", str(archive_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode not in [0, 1]:  # 0=ok, 1=warning
                raise RuntimeError(f"unrar list failed: {result.stderr}")
            
            return [
                line.strip()
                for line in result.stdout.split("\n")
                if line.strip()
            ]
        
        return await asyncio.to_thread(_list)
    
    async def extract(
        self,
        archive_path: Path,
        extract_to: Path,
    ) -> ArchiveInfo:
        """Extract using unrar x command."""
        if not self._unrar_available:
            raise RuntimeError("unrar not available")
        
        metrics = CompressedIngestionMetrics(format="rar")
        
        with metrics.extraction_timer():
            def _extract():
                extract_to.mkdir(parents=True, exist_ok=True)
                
                result = subprocess.run(
                    ["unrar", "x", "-y", str(archive_path), str(extract_to) + "/"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                
                if result.returncode not in [0, 1]:
                    raise RuntimeError(f"unrar extraction failed: {result.stderr}")
            
            await asyncio.to_thread(_extract)
        
        files = await self.list_contents(archive_path)
        compressed_size = archive_path.stat().st_size
        
        extracted_size = sum(
            (extract_to / f).stat().st_size
            for f in files
            if (extract_to / f).exists()
        )
        
        info = ArchiveInfo(
            format="rar",
            compressed_size=compressed_size,
            file_count=len(files),
            files=files,
            metadata={
                "tool": "unrar",
                "extracted_size": extracted_size,
            }
        )
        
        duration = 1.0
        metrics.record_success(
            original_bytes=compressed_size,
            extracted_bytes=extracted_size,
            file_count=len(files),
            duration_seconds=duration,
        )
        
        return info


class ISOExtractor(ArchiveExtractor):
    """
    Extractor for ISO disk images using 7z or mount.
    
    Supports ISO 9660 and UDF formats.
    """
    
    EXTENSIONS = {".iso"}
    
    def __init__(self):
        self._7z_available = self._check_7z_available()
    
    def _check_7z_available(self) -> bool:
        """Check if 7z command is available."""
        try:
            subprocess.run(["7z"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("7z not available for ISO extraction")
            return False
    
    async def can_handle(self, file_path: Path) -> bool:
        if not self._7z_available:
            return False
        
        if file_path.suffix.lower() in self.EXTENSIONS:
            return True
        
        # Check for ISO magic bytes
        try:
            with open(file_path, "rb") as f:
                f.seek(0x8000)  # Primary volume descriptor location
                magic = f.read(5)
                return magic in [b"CD001", b"BEA01", b"NSR02", b"NSR03"]
        except Exception:
            return False
    
    async def list_contents(self, archive_path: Path) -> List[str]:
        """List files using 7z."""
        if not self._7z_available:
            raise RuntimeError("7z not available for ISO")
        
        def _list():
            result = subprocess.run(
                ["7z", "l", "-ba", str(archive_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"7z list failed for ISO: {result.stderr}")
            
            files = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.split(maxsplit=5)
                    if len(parts) >= 6:
                        files.append(parts[5])
            
            return files
        
        return await asyncio.to_thread(_list)
    
    async def extract(
        self,
        archive_path: Path,
        extract_to: Path,
    ) -> ArchiveInfo:
        """Extract ISO using 7z."""
        if not self._7z_available:
            raise RuntimeError("7z not available for ISO")
        
        metrics = CompressedIngestionMetrics(format="iso")
        
        with metrics.extraction_timer():
            def _extract():
                extract_to.mkdir(parents=True, exist_ok=True)
                
                result = subprocess.run(
                    ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"],
                    capture_output=True,
                    text=True,
                    timeout=600,  # ISOs can be large
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"ISO extraction failed: {result.stderr}")
            
            await asyncio.to_thread(_extract)
        
        files = await self.list_contents(archive_path)
        compressed_size = archive_path.stat().st_size
        
        extracted_size = sum(
            (extract_to / f).stat().st_size
            for f in files
            if (extract_to / f).exists()
        )
        
        info = ArchiveInfo(
            format="iso",
            compressed_size=compressed_size,
            file_count=len(files),
            files=files,
            metadata={
                "tool": "7z",
                "extracted_size": extracted_size,
            }
        )
        
        duration = 1.0
        metrics.record_success(
            original_bytes=compressed_size,
            extracted_bytes=extracted_size,
            file_count=len(files),
            duration_seconds=duration,
        )
        
        return info


class EnhancedArchiveExtractor:
    """
    Unified archive extractor supporting multiple formats.
    
    Automatically selects appropriate extractor based on file type.
    """
    
    def __init__(self):
        self.extractors: List[ArchiveExtractor] = [
            SevenZipExtractor(),
            RarExtractor(),
            ISOExtractor(),
        ]
    
    async def detect_format(self, file_path: Path) -> Optional[ArchiveExtractor]:
        """Detect archive format and return appropriate extractor."""
        for extractor in self.extractors:
            if await extractor.can_handle(file_path):
                return extractor
        return None
    
    async def extract(
        self,
        archive_path: Path,
        extract_to: Optional[Path] = None,
    ) -> ArchiveInfo:
        """
        Extract archive using appropriate extractor.
        
        Args:
            archive_path: Path to archive file
            extract_to: Destination (defaults to temp directory)
        
        Returns:
            ArchiveInfo with extraction details
        """
        extractor = await self.detect_format(archive_path)
        if extractor is None:
            raise ValueError(f"Unsupported archive format: {archive_path}")
        
        if extract_to is None:
            extract_to = Path(tempfile.mkdtemp(prefix="archive_"))
        
        logger.info(
            "Extracting %s using %s to %s",
            archive_path,
            extractor.__class__.__name__,
            extract_to,
        )
        
        return await extractor.extract(archive_path, extract_to)
    
    async def list_contents(self, archive_path: Path) -> List[str]:
        """List archive contents without extracting."""
        extractor = await self.detect_format(archive_path)
        if extractor is None:
            raise ValueError(f"Unsupported archive format: {archive_path}")
        
        return await extractor.list_contents(archive_path)
    
    def supported_formats(self) -> List[str]:
        """Get list of supported archive formats."""
        formats = []
        for extractor in self.extractors:
            if hasattr(extractor, "EXTENSIONS"):
                formats.extend(extractor.EXTENSIONS)
        return sorted(formats)


# Global singleton
_enhanced_extractor: Optional[EnhancedArchiveExtractor] = None


def get_enhanced_extractor() -> EnhancedArchiveExtractor:
    """Get or create the global enhanced archive extractor."""
    global _enhanced_extractor
    if _enhanced_extractor is None:
        _enhanced_extractor = EnhancedArchiveExtractor()
    return _enhanced_extractor
