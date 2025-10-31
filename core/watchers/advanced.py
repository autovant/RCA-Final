"""
Advanced file watcher features: multi-config, scheduling, and cloud backends.

Provides support for:
- Multiple concurrent watcher configurations
- Scheduled/cron-based watching
- Custom processor registration
- Webhook targets
- S3 and Azure Blob storage backends
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from croniter import croniter

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WatcherSchedule:
    """Schedule configuration for time-based watching."""
    
    enabled: bool = True
    cron_expression: Optional[str] = None  # e.g., "0 */6 * * *" for every 6 hours
    start_time: Optional[time] = None  # Daily start time
    end_time: Optional[time] = None  # Daily end time
    days_of_week: Optional[Set[int]] = None  # 0=Monday, 6=Sunday
    timezone: str = "UTC"
    
    def is_active(self, check_time: Optional[datetime] = None) -> bool:
        """Check if schedule is currently active."""
        if not self.enabled:
            return False
        
        now = check_time or datetime.utcnow()
        
        # Check day of week
        if self.days_of_week is not None:
            if now.weekday() not in self.days_of_week:
                return False
        
        # Check time window
        if self.start_time and self.end_time:
            current_time = now.time()
            if self.start_time <= self.end_time:
                # Normal range (e.g., 9am-5pm)
                if not (self.start_time <= current_time <= self.end_time):
                    return False
            else:
                # Overnight range (e.g., 10pm-6am)
                if not (current_time >= self.start_time or current_time <= self.end_time):
                    return False
        
        return True
    
    def get_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate next scheduled run time (for cron-based schedules)."""
        if not self.enabled or not self.cron_expression:
            return None
        
        base_time = from_time or datetime.utcnow()
        try:
            cron = croniter(self.cron_expression, base_time)
            return cron.get_next(datetime)
        except Exception as exc:
            logger.error("Invalid cron expression '%s': %s", self.cron_expression, exc)
            return None


@dataclass
class WebhookTarget:
    """Configuration for webhook notifications."""
    
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    auth_token: Optional[str] = None
    retry_count: int = 3
    timeout_seconds: int = 30
    payload_template: Optional[str] = None
    
    def prepare_headers(self) -> Dict[str, str]:
        """Prepare headers with authentication."""
        headers = self.headers.copy()
        headers.setdefault("Content-Type", "application/json")
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        return headers
    
    def prepare_payload(self, event_data: Dict[str, Any]) -> str:
        """Prepare webhook payload from event data."""
        if self.payload_template:
            # Simple template substitution
            payload = self.payload_template
            for key, value in event_data.items():
                payload = payload.replace(f"{{{{{key}}}}}", str(value))
            return payload
        
        # Default: send raw JSON
        return json.dumps(event_data, default=str)


class StorageBackend(ABC):
    """Abstract base for storage backends (local, S3, Azure, etc.)."""
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        pass
    
    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read file contents."""
        pass
    
    @abstractmethod
    async def write(self, path: str, content: bytes) -> None:
        """Write file contents."""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file."""
        pass
    
    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """List files with optional prefix."""
        pass
    
    @abstractmethod
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get file metadata (size, modified time, etc.)."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
    
    async def exists(self, path: str) -> bool:
        full_path = self.base_path / path
        return full_path.exists()
    
    async def read(self, path: str) -> bytes:
        full_path = self.base_path / path
        return await asyncio.to_thread(full_path.read_bytes)
    
    async def write(self, path: str, content: bytes) -> None:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(full_path.write_bytes, content)
    
    async def delete(self, path: str) -> None:
        full_path = self.base_path / path
        if full_path.exists():
            await asyncio.to_thread(full_path.unlink)
    
    async def list(self, prefix: str = "") -> List[str]:
        search_path = self.base_path / prefix if prefix else self.base_path
        if not search_path.exists():
            return []
        
        def _list():
            if search_path.is_file():
                return [str(search_path.relative_to(self.base_path))]
            return [
                str(p.relative_to(self.base_path))
                for p in search_path.rglob("*")
                if p.is_file()
            ]
        
        return await asyncio.to_thread(_list)
    
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        full_path = self.base_path / path
        stat = await asyncio.to_thread(full_path.stat)
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "created": datetime.fromtimestamp(stat.st_ctime),
        }


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        
        # Lazy import to avoid hard dependency
        try:
            import aioboto3
            self.session = aioboto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region,
            )
        except ImportError:
            logger.error("aioboto3 not installed - S3 backend unavailable")
            raise
    
    def _get_key(self, path: str) -> str:
        """Get full S3 key with prefix."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    async def exists(self, path: str) -> bool:
        key = self._get_key(path)
        async with self.session.client("s3") as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except:
                return False
    
    async def read(self, path: str) -> bytes:
        key = self._get_key(path)
        async with self.session.client("s3") as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=key)
            return await response["Body"].read()
    
    async def write(self, path: str, content: bytes) -> None:
        key = self._get_key(path)
        async with self.session.client("s3") as s3:
            await s3.put_object(Bucket=self.bucket, Key=key, Body=content)
    
    async def delete(self, path: str) -> None:
        key = self._get_key(path)
        async with self.session.client("s3") as s3:
            await s3.delete_object(Bucket=self.bucket, Key=key)
    
    async def list(self, prefix: str = "") -> List[str]:
        search_prefix = self._get_key(prefix)
        async with self.session.client("s3") as s3:
            paginator = s3.get_paginator("list_objects_v2")
            keys = []
            async for page in paginator.paginate(
                Bucket=self.bucket,
                Prefix=search_prefix
            ):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        # Remove our prefix to get relative path
                        if self.prefix and key.startswith(f"{self.prefix}/"):
                            key = key[len(self.prefix) + 1:]
                        keys.append(key)
            return keys
    
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        key = self._get_key(path)
        async with self.session.client("s3") as s3:
            response = await s3.head_object(Bucket=self.bucket, Key=key)
            return {
                "size": response["ContentLength"],
                "modified": response["LastModified"],
                "etag": response["ETag"],
            }


class AzureBlobStorageBackend(StorageBackend):
    """Azure Blob Storage backend."""
    
    def __init__(
        self,
        container: str,
        prefix: str = "",
        connection_string: Optional[str] = None,
        account_url: Optional[str] = None,
    ):
        self.container = container
        self.prefix = prefix
        
        # Lazy import to avoid hard dependency
        try:
            from azure.storage.blob.aio import BlobServiceClient
            
            if connection_string:
                self.client = BlobServiceClient.from_connection_string(connection_string)
            elif account_url:
                self.client = BlobServiceClient(account_url)
            else:
                raise ValueError("Must provide connection_string or account_url")
        except ImportError:
            logger.error("azure-storage-blob not installed - Azure backend unavailable")
            raise
    
    def _get_blob_name(self, path: str) -> str:
        """Get full blob name with prefix."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    async def exists(self, path: str) -> bool:
        blob_name = self._get_blob_name(path)
        blob_client = self.client.get_blob_client(container=self.container, blob=blob_name)
        return await blob_client.exists()
    
    async def read(self, path: str) -> bytes:
        blob_name = self._get_blob_name(path)
        blob_client = self.client.get_blob_client(container=self.container, blob=blob_name)
        stream = await blob_client.download_blob()
        return await stream.readall()
    
    async def write(self, path: str, content: bytes) -> None:
        blob_name = self._get_blob_name(path)
        blob_client = self.client.get_blob_client(container=self.container, blob=blob_name)
        await blob_client.upload_blob(content, overwrite=True)
    
    async def delete(self, path: str) -> None:
        blob_name = self._get_blob_name(path)
        blob_client = self.client.get_blob_client(container=self.container, blob=blob_name)
        await blob_client.delete_blob()
    
    async def list(self, prefix: str = "") -> List[str]:
        search_prefix = self._get_blob_name(prefix)
        container_client = self.client.get_container_client(self.container)
        
        blobs = []
        async for blob in container_client.list_blobs(name_starts_with=search_prefix):
            name = blob.name
            # Remove our prefix to get relative path
            if self.prefix and name.startswith(f"{self.prefix}/"):
                name = name[len(self.prefix) + 1:]
            blobs.append(name)
        
        return blobs
    
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        blob_name = self._get_blob_name(path)
        blob_client = self.client.get_blob_client(container=self.container, blob=blob_name)
        properties = await blob_client.get_blob_properties()
        
        return {
            "size": properties.size,
            "modified": properties.last_modified,
            "created": properties.creation_time,
            "etag": properties.etag,
        }


@dataclass
class MultiWatcherConfig:
    """Configuration for managing multiple concurrent watchers."""
    
    config_id: str
    name: str
    enabled: bool = True
    watch_path: str = ""
    patterns: List[str] = field(default_factory=list)
    processor: Optional[str] = None
    schedule: Optional[WatcherSchedule] = None
    webhook: Optional[WebhookTarget] = None
    storage_backend: Optional[StorageBackend] = None
    priority: int = 0  # Higher priority watchers process first
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dict."""
        result = {
            "config_id": self.config_id,
            "name": self.name,
            "enabled": self.enabled,
            "watch_path": self.watch_path,
            "patterns": self.patterns,
            "processor": self.processor,
            "priority": self.priority,
            "metadata": self.metadata,
        }
        
        if self.schedule:
            result["schedule"] = {
                "enabled": self.schedule.enabled,
                "cron_expression": self.schedule.cron_expression,
                "timezone": self.schedule.timezone,
            }
        
        if self.webhook:
            result["webhook"] = {
                "url": self.webhook.url,
                "method": self.webhook.method,
            }
        
        return result


class CustomProcessorRegistry:
    """Registry for custom file processors."""
    
    def __init__(self):
        self._processors: Dict[str, Callable] = {}
    
    def register(
        self,
        name: str,
        processor: Callable[[Path, Dict[str, Any]], Any],
        overwrite: bool = False,
    ) -> None:
        """
        Register a custom processor function.
        
        Args:
            name: Unique processor name
            processor: Async function taking (file_path, metadata) and returning result
            overwrite: Allow overwriting existing processor
        """
        if name in self._processors and not overwrite:
            raise ValueError(f"Processor '{name}' already registered")
        
        self._processors[name] = processor
        logger.info("Registered custom processor: %s", name)
    
    def unregister(self, name: str) -> bool:
        """Unregister a processor. Returns True if removed."""
        if name in self._processors:
            del self._processors[name]
            logger.info("Unregistered processor: %s", name)
            return True
        return False
    
    def get(self, name: str) -> Optional[Callable]:
        """Get processor by name."""
        return self._processors.get(name)
    
    def list_processors(self) -> List[str]:
        """List all registered processor names."""
        return list(self._processors.keys())


# Global singletons
_custom_processor_registry: Optional[CustomProcessorRegistry] = None


def get_custom_processor_registry() -> CustomProcessorRegistry:
    """Get or create the global custom processor registry."""
    global _custom_processor_registry
    if _custom_processor_registry is None:
        _custom_processor_registry = CustomProcessorRegistry()
    return _custom_processor_registry
