"""Runtime helpers for the filesystem watcher service."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

import aiohttp
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from core.logging import get_logger, setup_logging

logger = get_logger(__name__)


class FileWatcherHandler(FileSystemEventHandler):
    """Handle filesystem events and orchestrate RCA job uploads."""

    def __init__(
        self,
        *,
        api_url: str,
        file_patterns: Sequence[str],
        debounce_seconds: int,
        max_file_size_mb: int,
        auth_token: Optional[str] = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.file_patterns = [pattern.strip() for pattern in file_patterns if pattern.strip()]
        self.debounce_seconds = debounce_seconds
        self.max_file_size_mb = max_file_size_mb
        self.auth_token = auth_token

        self.pending_files: Dict[str, float] = {}
        self.processed_files: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialise HTTP session."""

        headers: Dict[str, str] = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        timeout = aiohttp.ClientTimeout(total=300)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close(self) -> None:
        """Dispose of HTTP session."""

        if self.session is not None:
            await self.session.close()
            self.session = None

    # -- watchdog hooks -------------------------------------------------

    def on_created(self, event: FileSystemEvent) -> None:  # pragma: no cover - exercised via integration
        if event.is_directory:
            return

        file_path = event.src_path

        if not self._matches_pattern(file_path):
            return

        logger.info("Detected new file %s", file_path)
        self.pending_files[file_path] = asyncio.get_event_loop().time()

    def on_modified(self, event: FileSystemEvent) -> None:  # pragma: no cover - exercised via integration
        if event.is_directory:
            return

        file_path = event.src_path
        if file_path in self.pending_files:
            self.pending_files[file_path] = asyncio.get_event_loop().time()

    # -- internal helpers -----------------------------------------------

    def _matches_pattern(self, file_path: str) -> bool:
        path = Path(file_path)
        if not self.file_patterns:
            return True
        return any(path.match(pattern) for pattern in self.file_patterns)

    async def process_pending_files(self) -> None:
        """Upload files that have remained stable for the debounce interval."""

        now = asyncio.get_event_loop().time()
        files_to_process = []

        for file_path, timestamp in list(self.pending_files.items()):
            if now - timestamp >= self.debounce_seconds:
                if file_path not in self.processed_files:
                    files_to_process.append(file_path)
                self.pending_files.pop(file_path, None)

        for file_path in files_to_process:
            try:
                await self._process_file(file_path)
                self.processed_files.add(file_path)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Error processing file %s", file_path)

    async def _process_file(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():  # file could have been removed during debounce window
            logger.debug("Skipping %s; file no longer exists", file_path)
            return

        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            logger.warning(
                "File %s exceeds size limit %.2fMB > %sMB", file_path, size_mb, self.max_file_size_mb
            )
            return

        checksum = self._calculate_checksum(file_path)
        upload_result = await self._upload_file(file_path)

        if not upload_result:
            logger.error("Failed to upload %s", file_path)
            return

        file_id = upload_result.get("file_id")
        job_id = upload_result.get("job_id")

        logger.info(
            "Uploaded file %s (id=%s, job=%s, bytes=%s, checksum=%s)",
            file_path,
            file_id,
            job_id or "unknown",
            path.stat().st_size,
            checksum,
        )

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def _upload_file(self, file_path: str) -> Optional[Dict[str, Optional[str]]]:
        if self.session is None:
            logger.error("HTTP session not initialised; skipping upload")
            return None

        try:
            with open(file_path, "rb") as handle:
                data = aiohttp.FormData()
                data.add_field("file", handle, filename=Path(file_path).name)

                async with self.session.post(f"{self.api_url}/api/files/upload", data=data) as response:
                    if response.status in (200, 201):
                        payload = await response.json()
                        return {
                            "file_id": payload.get("id") or payload.get("file_id"),
                            "job_id": payload.get("job_id"),
                        }

                    logger.error(
                        "Upload failed for %s: status=%s, body=%s",
                        file_path,
                        response.status,
                        await response.text(),
                    )
        except Exception:  # pragma: no cover - network/IO failure
            logger.exception("Error uploading file %s", file_path)

        return None


async def run_file_watcher(
    *,
    api_url: str,
    watch_folder: str,
    file_patterns: Sequence[str],
    poll_interval: int,
    debounce_seconds: int,
    max_file_size_mb: int,
    auth_token: Optional[str] = None,
) -> None:
    """Run the watcher loop until cancelled."""

    handler = FileWatcherHandler(
        api_url=api_url,
        file_patterns=file_patterns,
        debounce_seconds=debounce_seconds,
        max_file_size_mb=max_file_size_mb,
        auth_token=auth_token,
    )

    await handler.initialize()

    path = Path(watch_folder)
    path.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(handler, str(path), recursive=True)
    observer.start()
    logger.info(
        "File watcher running | api_url=%s | watch_folder=%s | patterns=%s | poll_interval=%ss",
        api_url,
        path,
        ",".join(handler.file_patterns) if handler.file_patterns else "<all>",
        poll_interval,
    )

    try:
        while True:
            await handler.process_pending_files()
            await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
        raise
    except KeyboardInterrupt:  # pragma: no cover - manual termination
        logger.info("File watcher received shutdown signal")
    finally:
        observer.stop()
        await asyncio.to_thread(observer.join)
        await handler.close()
        logger.info("File watcher stopped")


def _parse_patterns(value: str) -> List[str]:
    if not value:
        return []
    parts = [part.strip() for part in value.split(",")]
    return [part for part in parts if part]


async def start_from_environment(*, configure_logging: bool = True) -> None:
    """Bootstrap the watcher service using environment variables."""

    if configure_logging:
        # Configure logging once for standalone execution.
        try:
            setup_logging()
        except Exception:  # pragma: no cover - fallback to default logging
            logging.basicConfig(level=logging.INFO)

    api_url = os.getenv("API_URL", "http://localhost:8000")
    watch_folder = os.getenv("WATCH_FOLDER", "/app/watch-folder")
    poll_interval = int(os.getenv("POLL_INTERVAL", "10"))
    debounce_seconds = int(os.getenv("DEBOUNCE_SECONDS", "5"))
    max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    file_patterns = _parse_patterns(os.getenv("FILE_PATTERNS", "*.log,*.txt,*.json"))
    auth_token = os.getenv("API_AUTH_TOKEN") or os.getenv("LOCAL_DEV_AUTH_TOKEN")

    await run_file_watcher(
        api_url=api_url,
        watch_folder=watch_folder,
        file_patterns=file_patterns,
        poll_interval=poll_interval,
        debounce_seconds=debounce_seconds,
        max_file_size_mb=max_file_size_mb,
        auth_token=auth_token,
    )


def run_cli() -> None:
    """CLI entry point used by scripts and ``python -m`` runners."""

    asyncio.run(start_from_environment())


__all__ = ["FileWatcherHandler", "run_file_watcher", "start_from_environment", "run_cli"]
