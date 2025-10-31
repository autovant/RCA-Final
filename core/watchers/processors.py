"""Custom watcher processor registry."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from core.logging import get_logger

logger = get_logger(__name__)

ProcessorCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ProcessorDefinition:
    """Describe an available watcher processor."""

    id: str
    name: str
    description: str
    handler: ProcessorCallable
    default_options: Dict[str, Any] = field(default_factory=dict)


class WatcherProcessorRegistry:
    """Registry for watcher event processors."""

    def __init__(self) -> None:
        self._definitions: Dict[str, ProcessorDefinition] = {}

    def register(self, definition: ProcessorDefinition) -> None:
        if definition.id in self._definitions:
            raise ValueError(f"Watcher processor '{definition.id}' already registered")
        self._definitions[definition.id] = definition
        logger.debug("Registered watcher processor %s", definition.id)

    def available(self) -> List[ProcessorDefinition]:
        return list(self._definitions.values())

    def get(self, processor_id: str) -> Optional[ProcessorDefinition]:
        return self._definitions.get(processor_id)

    async def run(self, processor_id: str, event_payload: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> None:
        definition = self.get(processor_id)
        if not definition:
            logger.warning("No watcher processor registered for id=%s", processor_id)
            return

        merged_options = dict(definition.default_options)
        if options:
            merged_options.update(options)

        try:
            await definition.handler(event_payload, merged_options)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Watcher processor '%s' failed", processor_id)


watcher_processor_registry = WatcherProcessorRegistry()


async def _log_event_processor(event_payload: Dict[str, Any], options: Dict[str, Any]) -> None:
    level = str(options.get("level", "info")).lower()
    message = options.get("message") or "Watcher event received"
    log_payload = {
        k: v
        for k, v in event_payload.items()
        if k in {"event_type", "job_id", "watcher_id", "created_at", "payload"}
    }
    if level == "debug":
        logger.debug("%s | payload=%s", message, log_payload)
    elif level == "warning":
        logger.warning("%s | payload=%s", message, log_payload)
    elif level == "error":
        logger.error("%s | payload=%s", message, log_payload)
    else:
        logger.info("%s | payload=%s", message, log_payload)


async def _asyncio_delay_processor(event_payload: Dict[str, Any], options: Dict[str, Any]) -> None:
    delay_seconds = float(options.get("delay_seconds", 1.0))
    await asyncio.sleep(max(0.0, delay_seconds))
    logger.debug(
        "Delayed watcher event %s by %ss", event_payload.get("event_type"), delay_seconds
    )


watcher_processor_registry.register(
    ProcessorDefinition(
        id="log-event",
        name="Event Logger",
        description="Emit structured log lines whenever a watcher event is received.",
        handler=_log_event_processor,
        default_options={"level": "info"},
    )
)

watcher_processor_registry.register(
    ProcessorDefinition(
        id="delay",
        name="Async Delay",
        description="Introduce an artificial delay for testing pipelines and ordering.",
        handler=_asyncio_delay_processor,
        default_options={"delay_seconds": 1.0},
    )
)


__all__ = [
    "ProcessorDefinition",
    "WatcherProcessorRegistry",
    "watcher_processor_registry",
]
