#!/usr/bin/env python3
"""
File Watcher Service for RCA Engine

Monitors configured directories for new log files and automatically
creates RCA analysis jobs when files are detected.
"""

import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import aiohttp
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RCAFileHandler(FileSystemEventHandler):
    """Handler for file system events that triggers RCA jobs."""

    def __init__(
        self,
        api_url: str,
        file_patterns: List[str],
        debounce_seconds: int = 5,
        max_file_size_mb: int = 100
    ):
        self.api_url = api_url
        self.file_patterns = file_patterns
        self.debounce_seconds = debounce_seconds
        self.max_file_size_mb = max_file_size_mb
        self.pending_files: Dict[str, float] = {}
        self.processed_files: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path
        
        # Check if file matches patterns
        if not self._matches_pattern(file_path):
            return

        # Add to pending files with timestamp
        self.pending_files[file_path] = time.time()
        logger.info(f"Detected new file: {file_path}")

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path
        
        # Update timestamp for pending files
        if file_path in self.pending_files:
            self.pending_files[file_path] = time.time()

    def _matches_pattern(self, file_path: str) -> bool:
        """Check if file matches any of the configured patterns."""
        path = Path(file_path)
        for pattern in self.file_patterns:
            if path.match(pattern):
                return True
        return False

    async def process_pending_files(self):
        """Process files that have been stable for the debounce period."""
        current_time = time.time()
        files_to_process = []

        # Find files that are ready to process
        for file_path, timestamp in list(self.pending_files.items()):
            if current_time - timestamp >= self.debounce_seconds:
                if file_path not in self.processed_files:
                    files_to_process.append(file_path)
                del self.pending_files[file_path]

        # Process each file
        for file_path in files_to_process:
            try:
                await self._process_file(file_path)
                self.processed_files.add(file_path)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")

    async def _process_file(self, file_path: str):
        """Process a single file by creating an RCA job."""
        path = Path(file_path)

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            logger.warning(
                f"File {file_path} exceeds max size "
                f"({file_size_mb:.2f}MB > {self.max_file_size_mb}MB)"
            )
            return

        # Calculate file checksum
        checksum = self._calculate_checksum(file_path)

        # Upload file to API
        file_id = await self._upload_file(file_path)
        if not file_id:
            logger.error(f"Failed to upload file: {file_path}")
            return

        # Create RCA job
        job_id = await self._create_job(file_id, file_path, checksum)
        if job_id:
            logger.info(f"Created RCA job {job_id} for file {file_path}")
        else:
            logger.error(f"Failed to create job for file: {file_path}")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def _upload_file(self, file_path: str) -> Optional[str]:
        """Upload file to the API."""
        if not self.session:
            return None

        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=Path(file_path).name)
                
                async with self.session.post(
                    f"{self.api_url}/api/files/upload",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('file_id')
                    else:
                        logger.error(
                            f"File upload failed with status {response.status}: "
                            f"{await response.text()}"
                        )
                        return None
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    async def _create_job(
        self,
        file_id: str,
        file_path: str,
        checksum: str
    ) -> Optional[str]:
        """Create an RCA analysis job."""
        if not self.session:
            return None

        try:
            payload = {
                "job_type": "rca_analysis",
                "input_manifest": {
                    "files": [file_id]
                },
                "source": {
                    "type": "file_watcher",
                    "path": file_path,
                    "checksum": checksum,
                    "detected_at": time.time()
                }
            }

            async with self.session.post(
                f"{self.api_url}/api/jobs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    return result.get('id')
                else:
                    logger.error(
                        f"Job creation failed with status {response.status}: "
                        f"{await response.text()}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return None


async def main():
    """Main entry point for the file watcher service."""
    # Get configuration from environment
    api_url = os.getenv('API_URL', 'http://localhost:8000')
    watch_folder = os.getenv('WATCH_FOLDER', '/app/watch-folder')
    poll_interval = int(os.getenv('POLL_INTERVAL', '10'))
    file_patterns = os.getenv('FILE_PATTERNS', '*.log,*.txt,*.json').split(',')
    debounce_seconds = int(os.getenv('DEBOUNCE_SECONDS', '5'))
    max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '100'))

    logger.info(f"Starting file watcher service")
    logger.info(f"API URL: {api_url}")
    logger.info(f"Watch folder: {watch_folder}")
    logger.info(f"File patterns: {file_patterns}")
    logger.info(f"Poll interval: {poll_interval}s")
    logger.info(f"Debounce: {debounce_seconds}s")
    logger.info(f"Max file size: {max_file_size_mb}MB")

    # Create watch folder if it doesn't exist
    Path(watch_folder).mkdir(parents=True, exist_ok=True)

    # Create file handler
    handler = RCAFileHandler(
        api_url=api_url,
        file_patterns=file_patterns,
        debounce_seconds=debounce_seconds,
        max_file_size_mb=max_file_size_mb
    )
    await handler.initialize()

    # Create observer
    observer = Observer()
    observer.schedule(handler, watch_folder, recursive=True)
    observer.start()

    logger.info(f"Watching directory: {watch_folder}")

    try:
        while True:
            # Process pending files
            await handler.process_pending_files()
            
            # Sleep for poll interval
            await asyncio.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Shutting down file watcher...")
        observer.stop()
        await handler.close()
    
    observer.join()
    logger.info("File watcher stopped")


if __name__ == "__main__":
    asyncio.run(main())
