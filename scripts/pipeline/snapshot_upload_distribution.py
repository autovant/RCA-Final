"""Snapshot recent upload distribution by file type for smoke packs."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, and_, select

from core.db.database import db_manager
from core.db.models import File, UploadTelemetryEventRecord

StageFilter = UploadTelemetryEventRecord.stage == "ingest"
StatusFilter = UploadTelemetryEventRecord.status.in_({"success", "partial"})


@dataclass
class UploadSample:
    """Lightweight view of a single upload telemetry row."""

    extension: str
    size_bytes: int


@dataclass
class FileTypeSnapshot:
    """Aggregated statistics for a file extension."""

    extension: str
    count: int
    percentage: float
    p50_size_bytes: int
    p95_size_bytes: int
    average_size_bytes: float

    def to_row(self) -> List[str]:
        return [
            self.extension,
            str(self.count),
            f"{self.percentage:.2f}",
            str(self.p50_size_bytes),
            str(self.p95_size_bytes),
            f"{self.average_size_bytes:.2f}",
        ]


@dataclass
class SnapshotPayload:
    """Rendered output payload for the snapshot command."""

    captured_at: str
    tenant_scope: str
    start: Optional[str]
    end: Optional[str]
    total_uploads: int
    file_types: List[FileTypeSnapshot]

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at,
            "tenant_scope": self.tenant_scope,
            "start": self.start,
            "end": self.end,
            "total_uploads": self.total_uploads,
            "file_types": [vars(item) for item in self.file_types],
        }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-id",
        action="append",
        dest="tenant_ids",
        help="Filter by tenant UUID (can be provided multiple times).",
    )
    parser.add_argument(
        "--start",
        type=_parse_datetime,
        help="ISO timestamp for earliest telemetry event (inclusive).",
    )
    parser.add_argument(
        "--end",
        type=_parse_datetime,
        help="ISO timestamp for latest telemetry event (exclusive).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of file types to include (default: 10).",
    )
    parser.add_argument(
        "--format",
        choices={"json", "csv"},
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write output. Defaults to stdout.",
    )
    return parser.parse_args(argv)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - argparse converts to error
        raise argparse.ArgumentTypeError(f"Invalid datetime: {value}") from exc


async def fetch_upload_samples(
    *,
    tenant_ids: Optional[Sequence[UUID]],
    start: Optional[datetime],
    end: Optional[datetime],
) -> List[UploadSample]:
    await db_manager.initialize()

    stmt: Select = (
        select(
            UploadTelemetryEventRecord.tenant_id,
            UploadTelemetryEventRecord.metadata,
            File.original_filename,
            File.filename,
            File.file_size,
        )
        .join(File, File.id == UploadTelemetryEventRecord.upload_id)
        .where(StageFilter, StatusFilter)
    )

    filters = []
    if tenant_ids:
        filters.append(UploadTelemetryEventRecord.tenant_id.in_(tenant_ids))
    if start:
        filters.append(UploadTelemetryEventRecord.created_at >= start)
    if end:
        filters.append(UploadTelemetryEventRecord.created_at < end)

    if filters:
        stmt = stmt.where(and_(*filters))

    async with db_manager.session() as session:
        result = await session.execute(stmt)
        rows = result.fetchall()

    samples: List[UploadSample] = []
    for tenant_id, metadata, original_filename, filename, file_size in rows:
        size = int(file_size or 0)
        name_source = original_filename or filename or "unknown"
        extension = _normalise_extension(name_source, metadata)
        samples.append(UploadSample(extension=extension, size_bytes=size))

    await db_manager.close()
    return samples


def _normalise_extension(name: str, metadata: Optional[dict]) -> str:
    if metadata and isinstance(metadata, dict):
        ext = metadata.get("extension")
        if isinstance(ext, str) and ext.strip():
            return ext.strip().lstrip(".").lower()

    if "." in name:
        return name.rsplit(".", 1)[-1].lower() or "unknown"
    return "unknown"


def compute_file_type_stats(
    samples: Iterable[UploadSample],
    *,
    limit: int,
) -> Tuple[int, List[FileTypeSnapshot]]:
    buckets: dict[str, List[int]] = {}
    total = 0
    for sample in samples:
        total += 1
        if sample.size_bytes < 0:
            continue
        bucket = buckets.setdefault(sample.extension or "unknown", [])
        bucket.append(sample.size_bytes)

    items: List[FileTypeSnapshot] = []
    for extension, sizes in buckets.items():
        sizes_sorted = sorted(sizes)
        count = len(sizes_sorted)
        items.append(
            FileTypeSnapshot(
                extension=extension,
                count=count,
                percentage=(count / total * 100.0) if total else 0.0,
                p50_size_bytes=_percentile(sizes_sorted, 0.5),
                p95_size_bytes=_percentile(sizes_sorted, 0.95),
                average_size_bytes=mean(sizes_sorted) if sizes_sorted else 0.0,
            )
        )

    items.sort(key=lambda entry: (-entry.count, entry.extension))
    return total, items[: max(limit, 1)]


def _percentile(values: Sequence[int], quantile: float) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return int(values[0])
    index = (len(values) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    fraction = index - lower
    interpolated = values[lower] + (values[upper] - values[lower]) * fraction
    return int(round(interpolated))


def render_snapshot(
    sample_total: int,
    file_types: List[FileTypeSnapshot],
    *,
    tenant_ids: Optional[Sequence[UUID]],
    start: Optional[datetime],
    end: Optional[datetime],
) -> SnapshotPayload:
    captured_at = datetime.now().astimezone().isoformat()
    tenant_scope = "all-tenants"
    if tenant_ids:
        tenant_scope = ",".join(str(tid) for tid in tenant_ids)

    return SnapshotPayload(
        captured_at=captured_at,
        tenant_scope=tenant_scope,
        start=start.isoformat() if start else None,
        end=end.isoformat() if end else None,
        total_uploads=sample_total,
        file_types=file_types,
    )


def write_output(payload: SnapshotPayload, *, fmt: str, output: Optional[Path]) -> None:
    if fmt == "json":
        text = json.dumps(payload.to_dict(), indent=2)
        _write_text(text, output)
        return

    header = [
        "extension",
        "count",
        "percentage",
        "p50_size_bytes",
        "p95_size_bytes",
        "average_size_bytes",
    ]
    rows = [header] + [item.to_row() for item in payload.file_types]
    if output:
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        return

    writer = csv.writer(sys.stdout)
    writer.writerows(rows)


def _write_text(text: str, output: Optional[Path]) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text)


async def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    tenant_ids = None
    if args.tenant_ids:
        tenant_ids = [UUID(value) for value in args.tenant_ids]

    samples = await fetch_upload_samples(
        tenant_ids=tenant_ids,
        start=args.start,
        end=args.end,
    )
    total, file_types = compute_file_type_stats(samples, limit=args.limit)
    payload = render_snapshot(
        total,
        file_types,
        tenant_ids=tenant_ids,
        start=args.start,
        end=args.end,
    )
    write_output(payload, fmt=args.format, output=args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(asyncio.run(main()))
