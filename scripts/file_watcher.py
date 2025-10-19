#!/usr/bin/env python3
"""Legacy entry point retained for backwards compatibility."""

from core.watchers.runner import run_cli


if __name__ == "__main__":  # pragma: no cover - CLI hook
    run_cli()
