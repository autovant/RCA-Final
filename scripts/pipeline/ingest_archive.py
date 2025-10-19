#!/usr/bin/env python3
"""CLI tool for archive ingestion with safeguard checks.

This script validates and extracts archive files with guardrail enforcement,
displaying warnings when potential decompression bombs or excessive members
are detected.

Usage:
    python scripts/pipeline/ingest_archive.py <archive_path> [--destination <path>] [--strict]

Examples:
    # Extract with default safeguards
    python scripts/pipeline/ingest_archive.py logs.tar.gz

    # Extract to specific destination
    python scripts/pipeline/ingest_archive.py data.zip --destination ./extracted/

    # Strict mode - block on any warnings
    python scripts/pipeline/ingest_archive.py large.tar.bz2 --strict
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from core.files.extraction import ArchiveExtractor, ArchiveExtractionError
from core.files.validation import validate_archive_before_extraction, map_extraction_error
from core.files.validators import SafeguardConfig


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ WARNING: {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ ERROR: {text}{Colors.RESET}")


def print_info(label: str, value: str) -> None:
    """Print an info line."""
    print(f"{Colors.BOLD}{label}:{Colors.RESET} {value}")


def ingest_archive(
    archive_path: Path,
    destination: Optional[Path] = None,
    strict: bool = False,
    safeguard_config: Optional[SafeguardConfig] = None,
) -> bool:
    """Ingest and extract an archive with safeguard checks.
    
    Args:
        archive_path: Path to archive file
        destination: Optional extraction destination
        strict: If True, treat warnings as errors
        safeguard_config: Optional safeguard configuration
    
    Returns:
        True if successful, False otherwise
    """
    print_header(f"Archive Ingestion: {archive_path.name}")

    # Validate archive exists
    if not archive_path.exists():
        print_error(f"Archive not found: {archive_path}")
        return False

    # Display archive info
    archive_size = archive_path.stat().st_size
    archive_size_mb = archive_size / (1024 * 1024)
    print_info("Archive Type", archive_path.suffix)
    print_info("Archive Size", f"{archive_size_mb:.2f} MB ({archive_size:,} bytes)")

    # Run pre-extraction safeguard checks
    print(f"\n{Colors.BOLD}Running safeguard checks...{Colors.RESET}")
    violations = validate_archive_before_extraction(
        archive_path,
        safeguard_config=safeguard_config,
    )

    if violations:
        print(f"\n{Colors.BOLD}Safeguard Violations Detected:{Colors.RESET}")
        for violation in violations:
            if violation.code in ("excessive_decompression_ratio", "excessive_member_count", "path_traversal_attempt"):
                print_error(f"{violation.message}")
                if violation.detail:
                    print(f"  Details: {violation.detail}")
            else:
                print_warning(f"{violation.message}")
                if violation.detail:
                    print(f"  Details: {violation.detail}")

        # Check if we should block extraction
        has_critical = any(
            v.code in ("excessive_decompression_ratio", "excessive_member_count", "path_traversal_attempt")
            for v in violations
        )

        if has_critical or strict:
            print_error("\nExtraction blocked due to safeguard violations")
            return False
        else:
            print_warning("\nProceeding with extraction despite warnings...")
    else:
        print_success("All safeguard checks passed")

    # Extract archive
    print(f"\n{Colors.BOLD}Extracting archive...{Colors.RESET}")
    try:
        extractor = ArchiveExtractor()
        result = extractor.extract(archive_path, destination=destination)

        # Display extraction results
        print_success(f"Extraction completed in {result.duration_seconds:.2f}s")
        print_info("Files Extracted", str(len(result.files)))
        print_info("Total Size", f"{result.total_size_bytes / (1024 * 1024):.2f} MB")
        print_info("Destination", str(result.destination))

        # Display decompression ratio
        if archive_size > 0:
            ratio = result.total_size_bytes / archive_size
            ratio_color = Colors.GREEN if ratio < 50 else Colors.YELLOW if ratio < 100 else Colors.RED
            print(f"{Colors.BOLD}Decompression Ratio:{Colors.RESET} {ratio_color}{ratio:.1f}:1{Colors.RESET}")

        # Display warnings if any
        if result.warnings:
            print(f"\n{Colors.BOLD}Extraction Warnings:{Colors.RESET}")
            for warning in result.warnings:
                print_warning(warning)

        # Display sample of extracted files
        if result.files:
            print(f"\n{Colors.BOLD}Extracted Files (first 10):{Colors.RESET}")
            for i, file in enumerate(result.files[:10]):
                file_size_kb = file.size_bytes / 1024
                print(f"  {i + 1}. {file.original_path} ({file_size_kb:.1f} KB)")
            if len(result.files) > 10:
                print(f"  ... and {len(result.files) - 10} more files")

        return True

    except ArchiveExtractionError as e:
        violation = map_extraction_error(e)
        print_error(f"{violation.message}")
        if violation.detail:
            print(f"  Details: {violation.detail}")
        return False
    except Exception as e:
        print_error(f"Unexpected error during extraction: {e}")
        return False


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest and extract archive files with safeguard checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported Formats:
  - .zip       - ZIP archives
  - .gz        - Gzip compressed files
  - .bz2       - Bzip2 compressed files
  - .xz        - XZ/LZMA compressed files
  - .tar       - Uncompressed tar archives
  - .tar.gz    - Gzip compressed tar (.tgz also supported)
  - .tar.bz2   - Bzip2 compressed tar (.tbz2 also supported)
  - .tar.xz    - XZ compressed tar (.txz also supported)

Safeguard Thresholds (defaults):
  - Max decompression ratio: 100:1
  - Max member count: 10,000 files
  - Min size for ratio check: 1 KB

Examples:
  # Basic extraction
  %(prog)s logs.tar.gz

  # Extract to specific location
  %(prog)s data.zip --destination ./extracted/

  # Strict mode (block on warnings)
  %(prog)s suspicious.tar.bz2 --strict

  # Custom safeguard limits
  %(prog)s large.zip --max-ratio 200 --max-members 50000
        """,
    )

    parser.add_argument(
        "archive",
        type=Path,
        help="Path to archive file to extract",
    )
    parser.add_argument(
        "-d",
        "--destination",
        type=Path,
        help="Destination directory for extraction (default: temp directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors and block extraction",
    )
    parser.add_argument(
        "--max-ratio",
        type=float,
        default=100.0,
        help="Maximum decompression ratio (default: 100)",
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=10000,
        help="Maximum number of archive members (default: 10000)",
    )

    args = parser.parse_args()

    # Create safeguard config
    safeguard_config = SafeguardConfig(
        max_decompression_ratio=args.max_ratio,
        max_member_count=args.max_members,
    )

    # Run ingestion
    success = ingest_archive(
        archive_path=args.archive,
        destination=args.destination,
        strict=args.strict,
        safeguard_config=safeguard_config,
    )

    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Ingestion completed successfully{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Ingestion failed{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
