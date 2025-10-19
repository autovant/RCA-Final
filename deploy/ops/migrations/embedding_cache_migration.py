"""Operational helper for the embedding cache Alembic migration.

This script gives operators a single entry point to apply or rollback the
`8f2b2fe76fd4` migration that introduces the `embedding_cache` table. It wraps
`alembic` invocations so rollouts remain consistent across environments.

Usage examples (run from repository root):

    python deploy/ops/migrations/embedding_cache_migration.py apply
    python deploy/ops/migrations/embedding_cache_migration.py rollback

Environment preparation:
- Ensure the `DATABASE_URL` environment variable points at the target Postgres
  instance with the same credentials used by the application.
- Activate the same virtual environment used for regular backend operations so
  Alembic picks up the expected configuration and dependencies.

Forward path (apply):
1. `alembic upgrade 8f2b2fe76fd4`
   - Creates the `embedding_cache` table with indexes on tenant, last-accessed,
     and embedding vector references.
   - Enforces the unique constraint on `(tenant_id, content_sha256, model)` plus
     validation constraints for SHA length, hit counts, and expiry ordering.
2. Record the execution in the release tracker for auditing.

Rollback path:
1. `alembic downgrade 4b9a5b36a142`
   - Drops the `embedding_cache` table and all related indexes.
   - Safe to run only when the cache feature flag is disabled for every tenant
     and no eviction jobs are running.
2. Confirm that downstream services no longer access the table before
   re-enabling the feature.

The script emits clear log-style messages so operators can copy them into change
management tickets.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List

REVISION_ID = "8f2b2fe76fd4"
PREVIOUS_REVISION_ID = "4b9a5b36a142"


def _run_alembic(args: List[str]) -> None:
    """Run an Alembic command, surfacing errors verbosely."""

    command = [sys.executable, "-m", "alembic", *args]
    print(f"[embedding-cache-migration] Running: {' '.join(command)}")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(
            f"Alembic command failed with exit code {completed.returncode}"
        )


def _apply() -> None:
    print("[embedding-cache-migration] Applying migration")
    _run_alembic(["upgrade", REVISION_ID])
    print("[embedding-cache-migration] Migration applied successfully")


def _rollback() -> None:
    print("[embedding-cache-migration] Rolling back migration")
    _run_alembic(["downgrade", PREVIOUS_REVISION_ID])
    print("[embedding-cache-migration] Migration rolled back successfully")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply or rollback the embedding cache Alembic migration."
        )
    )
    parser.add_argument(
        "action",
        choices={"apply", "rollback"},
        help="Desired migration action",
    )
    parsed = parser.parse_args()

    if parsed.action == "apply":
        _apply()
    else:
        _rollback()


if __name__ == "__main__":
    main()
