"""Tests for extended archive format support and safeguards."""

import bz2
import gzip
import lzma
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest

from core.files.extraction import ArchiveExtractor, UnsupportedArchiveTypeError
from core.files.validators import SafeguardConfig, evaluate_archive_safeguards


class TestExtendedArchiveFormats:
    """Test support for .bz2, .xz, .tar.gz, .tar.bz2, .tar.xz formats."""

    def test_extract_bzip2_file(self, tmp_path: Path):
        """Test extracting a .bz2 compressed file."""
        # Create a test file
        content = b"Test content for bzip2 compression" * 100
        archive_path = tmp_path / "test.txt.bz2"

        with bz2.open(archive_path, "wb") as f:
            f.write(content)

        # Extract
        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "test.txt"
            extracted_content = result.files[0].path.read_bytes()
            assert extracted_content == content
        finally:
            result.cleanup()

    def test_extract_xz_file(self, tmp_path: Path):
        """Test extracting an .xz compressed file."""
        content = b"Test content for XZ/LZMA compression" * 100
        archive_path = tmp_path / "test.txt.xz"

        with lzma.open(archive_path, "wb") as f:
            f.write(content)

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "test.txt"
            extracted_content = result.files[0].path.read_bytes()
            assert extracted_content == content
        finally:
            result.cleanup()

    def test_extract_tar_gz(self, tmp_path: Path):
        """Test extracting a .tar.gz archive."""
        # Create a tar.gz with multiple files
        archive_path = tmp_path / "test.tar.gz"

        with tarfile.open(archive_path, "w:gz") as tar:
            # Add file 1
            file1 = tmp_path / "file1.txt"
            file1.write_text("Content of file 1")
            tar.add(file1, arcname="file1.txt")

            # Add file 2 in subdirectory
            file2 = tmp_path / "file2.txt"
            file2.write_text("Content of file 2")
            tar.add(file2, arcname="subdir/file2.txt")

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 2
            assert any(f.original_path == "file1.txt" for f in result.files)
            assert any(f.original_path == "subdir/file2.txt" for f in result.files)
        finally:
            result.cleanup()

    def test_extract_tar_bz2(self, tmp_path: Path):
        """Test extracting a .tar.bz2 archive."""
        archive_path = tmp_path / "test.tar.bz2"

        with tarfile.open(archive_path, "w:bz2") as tar:
            file1 = tmp_path / "data.log"
            file1.write_text("Log data here")
            tar.add(file1, arcname="data.log")

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "data.log"
        finally:
            result.cleanup()

    def test_extract_tar_xz(self, tmp_path: Path):
        """Test extracting a .tar.xz archive."""
        archive_path = tmp_path / "test.tar.xz"

        with tarfile.open(archive_path, "w:xz") as tar:
            file1 = tmp_path / "config.json"
            file1.write_text('{"key": "value"}')
            tar.add(file1, arcname="config.json")

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "config.json"
        finally:
            result.cleanup()

    def test_extract_tgz_shorthand(self, tmp_path: Path):
        """Test extracting .tgz shorthand format."""
        archive_path = tmp_path / "test.tgz"

        with tarfile.open(archive_path, "w:gz") as tar:
            file1 = tmp_path / "readme.txt"
            file1.write_text("README content")
            tar.add(file1, arcname="readme.txt")

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "readme.txt"
        finally:
            result.cleanup()

    def test_extract_plain_tar(self, tmp_path: Path):
        """Test extracting uncompressed .tar archive."""
        archive_path = tmp_path / "test.tar"

        with tarfile.open(archive_path, "w") as tar:
            file1 = tmp_path / "plain.txt"
            file1.write_text("Plain tar content")
            tar.add(file1, arcname="plain.txt")

        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path)

        try:
            assert len(result.files) == 1
            assert result.files[0].original_path == "plain.txt"
        finally:
            result.cleanup()

    def test_unsupported_format_raises_error(self, tmp_path: Path):
        """Test that unsupported formats raise appropriate error."""
        archive_path = tmp_path / "test.rar"
        archive_path.write_bytes(b"fake RAR content")

        extractor = ArchiveExtractor()
        with pytest.raises(UnsupportedArchiveTypeError):
            extractor.extract(archive_path)


class TestArchiveSafeguards:
    """Test safeguard checks for decompression bombs and excessive members."""

    def test_excessive_decompression_ratio_detected_zip(self, tmp_path: Path):
        """Test detection of high decompression ratio in ZIP (potential bomb)."""
        archive_path = tmp_path / "bomb.zip"

        # Create a ZIP with high compression ratio
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Highly compressible data (repeated zeros)
            large_content = b"\x00" * (10 * 1024 * 1024)  # 10MB of zeros
            zf.writestr("zeros.bin", large_content)

        config = SafeguardConfig(max_decompression_ratio=50)
        violations = evaluate_archive_safeguards(archive_path, config=config)

        assert any(v.code == "excessive_decompression_ratio" for v in violations)

    def test_excessive_member_count_detected_zip(self, tmp_path: Path):
        """Test detection of excessive member count in ZIP."""
        archive_path = tmp_path / "many_files.zip"

        with zipfile.ZipFile(archive_path, "w") as zf:
            # Create archive with many small files
            for i in range(150):
                zf.writestr(f"file_{i}.txt", f"content {i}")

        config = SafeguardConfig(max_member_count=100)
        violations = evaluate_archive_safeguards(archive_path, config=config)

        assert any(v.code == "excessive_member_count" for v in violations)

    def test_excessive_decompression_ratio_detected_tar(self, tmp_path: Path):
        """Test detection of high decompression ratio in TAR.GZ."""
        archive_path = tmp_path / "bomb.tar.gz"

        # Create temp file with highly compressible data
        temp_file = tmp_path / "zeros.bin"
        temp_file.write_bytes(b"\x00" * (10 * 1024 * 1024))  # 10MB zeros

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_file, arcname="zeros.bin")

        config = SafeguardConfig(max_decompression_ratio=50)
        violations = evaluate_archive_safeguards(archive_path, config=config)

        assert any(v.code == "excessive_decompression_ratio" for v in violations)

    def test_path_traversal_detected_zip(self, tmp_path: Path):
        """Test detection of path traversal attempts in ZIP."""
        archive_path = tmp_path / "traversal.zip"

        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "malicious content")

        violations = evaluate_archive_safeguards(archive_path)

        assert any(v.code == "path_traversal_attempt" for v in violations)

    def test_path_traversal_detected_tar(self, tmp_path: Path):
        """Test detection of path traversal attempts in TAR."""
        archive_path = tmp_path / "traversal.tar"

        temp_file = tmp_path / "malicious.txt"
        temp_file.write_text("malicious")

        with tarfile.open(archive_path, "w") as tar:
            tar.add(temp_file, arcname="../../../etc/shadow")

        violations = evaluate_archive_safeguards(archive_path)

        assert any(v.code in ("path_traversal_attempt", "absolute_path_detected") for v in violations)

    def test_safe_archive_passes_safeguards(self, tmp_path: Path):
        """Test that a normal safe archive passes all safeguard checks."""
        archive_path = tmp_path / "safe.zip"

        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("file1.txt", "Normal content here")
            zf.writestr("subdir/file2.txt", "More normal content")

        violations = evaluate_archive_safeguards(archive_path)

        # Should have no violations
        assert len(violations) == 0

    def test_small_archive_skips_ratio_check(self, tmp_path: Path):
        """Test that very small archives skip decompression ratio check."""
        archive_path = tmp_path / "tiny.zip"

        # Create a very small archive (below min threshold)
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("small.txt", "x")

        config = SafeguardConfig(
            max_decompression_ratio=1,  # Would fail if checked
            min_compressed_size_for_ratio_check=1024,  # 1KB minimum
        )
        violations = evaluate_archive_safeguards(archive_path, config=config)

        # Should not have decompression ratio violation
        assert not any(v.code == "excessive_decompression_ratio" for v in violations)


class TestExtractionWithSafeguards:
    """Test extraction respects size and timeout limits even with new formats."""

    def test_tar_gz_respects_size_limit(self, tmp_path: Path):
        """Test that tar.gz extraction enforces size limits."""
        archive_path = tmp_path / "large.tar.gz"

        # Create a tar.gz with content exceeding size limit
        temp_file = tmp_path / "large.bin"
        temp_file.write_bytes(b"x" * (200 * 1024))  # 200KB

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_file, arcname="large.bin")

        # Set a low size limit
        extractor = ArchiveExtractor(size_limit_bytes=100 * 1024)

        from core.files.extraction import ExtractionSizeLimitExceeded

        with pytest.raises(ExtractionSizeLimitExceeded):
            extractor.extract(archive_path)

    def test_bzip2_respects_size_limit(self, tmp_path: Path):
        """Test that .bz2 extraction enforces size limits."""
        archive_path = tmp_path / "large.bz2"
        large_content = b"y" * (200 * 1024)  # 200KB

        with bz2.open(archive_path, "wb") as f:
            f.write(large_content)

        extractor = ArchiveExtractor(size_limit_bytes=100 * 1024)

        from core.files.extraction import ExtractionSizeLimitExceeded

        with pytest.raises(ExtractionSizeLimitExceeded):
            extractor.extract(archive_path)
