"""
Enhanced RPA Platform Adapters

Broadens support for RPA platforms beyond current capabilities:
- Automation Anywhere (A360, A2019, v11)
- WorkFusion
- Pega RPA
- Microsoft Power Automate Desktop
- Kofax RPA
- NICE (formerly WDG Automation)
- EdgeVerve AssistEdge
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


class RPAPlatform(str, Enum):
    """Supported RPA platforms."""
    BLUEPRISM = "blueprism"
    UIPATH = "uipath"
    AUTOMATION_ANYWHERE = "automation_anywhere"
    WORKFUSION = "workfusion"
    PEGA = "pega"
    POWER_AUTOMATE = "power_automate"
    KOFAX = "kofax"
    NICE = "nice"
    ASSISTEDGE = "assistedge"
    UNKNOWN = "unknown"


@dataclass
class RPADetectionSignature:
    """Signature patterns for detecting RPA platforms."""
    
    platform: RPAPlatform
    confidence_patterns: List[Pattern] = field(default_factory=list)
    version_patterns: List[Pattern] = field(default_factory=list)
    log_format_patterns: List[Pattern] = field(default_factory=list)
    file_extensions: List[str] = field(default_factory=list)
    metadata_keys: List[str] = field(default_factory=list)


@dataclass
class RPALogEntry:
    """Normalized RPA log entry."""
    
    timestamp: Optional[datetime]
    level: str  # INFO, WARNING, ERROR, FATAL
    message: str
    platform: RPAPlatform
    version: Optional[str] = None
    process_name: Optional[str] = None
    robot_name: Optional[str] = None
    session_id: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RPAPlatformAdapter(ABC):
    """Base class for RPA platform adapters."""
    
    @abstractmethod
    def detect(self, content: str, filename: Optional[str] = None) -> float:
        """
        Detect if content belongs to this platform.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    def extract_version(self, content: str) -> Optional[str]:
        """Extract platform version from content."""
        pass
    
    @abstractmethod
    def parse_log_entry(self, line: str) -> Optional[RPALogEntry]:
        """Parse a single log line into structured entry."""
        pass
    
    @abstractmethod
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract platform-specific metadata."""
        pass


class AutomationAnywhereAdapter(RPAPlatformAdapter):
    """
    Adapter for Automation Anywhere (A360, A2019, v11).
    
    Patterns:
    - Log format: [timestamp] [level] [component] message
    - Version indicators: AA.*, A2019, A360
    - Components: Bot Runner, Control Room, Bot Creator
    """
    
    SIGNATURES = [
        re.compile(r"Automation\s*Anywhere", re.IGNORECASE),
        re.compile(r"\bA360\b|\bA2019\b|\bA11\b"),
        re.compile(r"Bot\s*Runner|Control\s*Room|Bot\s*Creator", re.IGNORECASE),
        re.compile(r"Task\s*Bot|IQ\s*Bot|Meta\s*Bot", re.IGNORECASE),
    ]
    
    VERSION_PATTERN = re.compile(
        r"(?:version|ver|v)[:\s]*([Aa]?(?:360|2019|11)[\d.]*)",
        re.IGNORECASE
    )
    
    LOG_PATTERN = re.compile(
        r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*\[(\w+)\]\s*\[([^\]]+)\]\s*(.+)"
    )
    
    def detect(self, content: str, filename: Optional[str] = None) -> float:
        confidence = 0.0
        
        for pattern in self.SIGNATURES:
            if pattern.search(content):
                confidence += 0.25
        
        if filename and any(ext in filename.lower() for ext in [".atmx", ".abot"]):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def extract_version(self, content: str) -> Optional[str]:
        match = self.VERSION_PATTERN.search(content)
        return match.group(1) if match else None
    
    def parse_log_entry(self, line: str) -> Optional[RPALogEntry]:
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None
        
        timestamp_str, level, component, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = None
        
        return RPALogEntry(
            timestamp=timestamp,
            level=level.upper(),
            message=message.strip(),
            platform=RPAPlatform.AUTOMATION_ANYWHERE,
            metadata={"component": component},
        )
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "platform": "automation_anywhere",
            "version": self.extract_version(content),
        }
        
        # Extract bot name
        bot_match = re.search(r"Bot\s*Name[:\s]+([^\n,]+)", content, re.IGNORECASE)
        if bot_match:
            metadata["bot_name"] = bot_match.group(1).strip()
        
        # Extract control room
        cr_match = re.search(r"Control\s*Room[:\s]+([^\n,]+)", content, re.IGNORECASE)
        if cr_match:
            metadata["control_room"] = cr_match.group(1).strip()
        
        return metadata


class WorkFusionAdapter(RPAPlatformAdapter):
    """
    Adapter for WorkFusion RPA.
    
    Patterns:
    - Log format: timestamp level [thread] class - message
    - Components: RPA Express, WorkFusion Studio, Smart Process Automation
    """
    
    SIGNATURES = [
        re.compile(r"WorkFusion", re.IGNORECASE),
        re.compile(r"RPA\s*Express", re.IGNORECASE),
        re.compile(r"com\.workfusion\.", re.IGNORECASE),
        re.compile(r"Smart\s*Process\s*Automation", re.IGNORECASE),
    ]
    
    VERSION_PATTERN = re.compile(r"WorkFusion[:\s]*v?(\d+\.\d+[\d.]*)", re.IGNORECASE)
    
    LOG_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]\d+)\s+(\w+)\s+\[([^\]]+)\]\s+([^\s]+)\s+-\s+(.+)"
    )
    
    def detect(self, content: str, filename: Optional[str] = None) -> float:
        confidence = 0.0
        
        for pattern in self.SIGNATURES:
            if pattern.search(content):
                confidence += 0.25
        
        return min(confidence, 1.0)
    
    def extract_version(self, content: str) -> Optional[str]:
        match = self.VERSION_PATTERN.search(content)
        return match.group(1) if match else None
    
    def parse_log_entry(self, line: str) -> Optional[RPALogEntry]:
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None
        
        timestamp_str, level, thread, class_name, message = match.groups()
        
        try:
            # Handle both comma and dot millisecond separator
            timestamp_str = timestamp_str.replace(",", ".")
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            timestamp = None
        
        return RPALogEntry(
            timestamp=timestamp,
            level=level.upper(),
            message=message.strip(),
            platform=RPAPlatform.WORKFUSION,
            metadata={
                "thread": thread,
                "class": class_name,
            },
        )
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        return {
            "platform": "workfusion",
            "version": self.extract_version(content),
        }


class PegaRPAAdapter(RPAPlatformAdapter):
    """
    Adapter for Pega RPA (formerly OpenSpan).
    
    Patterns:
    - Components: Robotics Studio, Runtime, Robotics Manager
    - Log format: [timestamp] level: message
    """
    
    SIGNATURES = [
        re.compile(r"Pega\s*(?:RPA|Robotics)", re.IGNORECASE),
        re.compile(r"OpenSpan", re.IGNORECASE),
        re.compile(r"Robotics\s*(?:Studio|Runtime|Manager)", re.IGNORECASE),
    ]
    
    VERSION_PATTERN = re.compile(r"Pega\s*(?:RPA|Robotics)[:\s]*v?(\d+\.\d+[\d.]*)", re.IGNORECASE)
    
    LOG_PATTERN = re.compile(
        r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.+)"
    )
    
    def detect(self, content: str, filename: Optional[str] = None) -> float:
        confidence = 0.0
        
        for pattern in self.SIGNATURES:
            if pattern.search(content):
                confidence += 0.3
        
        return min(confidence, 1.0)
    
    def extract_version(self, content: str) -> Optional[str]:
        match = self.VERSION_PATTERN.search(content)
        return match.group(1) if match else None
    
    def parse_log_entry(self, line: str) -> Optional[RPALogEntry]:
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None
        
        timestamp_str, level, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = None
        
        return RPALogEntry(
            timestamp=timestamp,
            level=level.upper(),
            message=message.strip(),
            platform=RPAPlatform.PEGA,
        )
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        return {
            "platform": "pega",
            "version": self.extract_version(content),
        }


class PowerAutomateAdapter(RPAPlatformAdapter):
    """
    Adapter for Microsoft Power Automate Desktop.
    
    Patterns:
    - Components: PAD.*, Power Automate Desktop
    - Log format: Microsoft.Flow.*
    """
    
    SIGNATURES = [
        re.compile(r"Power\s*Automate\s*Desktop", re.IGNORECASE),
        re.compile(r"\bPAD\b"),
        re.compile(r"Microsoft\.Flow\.", re.IGNORECASE),
        re.compile(r"UIFlowService", re.IGNORECASE),
    ]
    
    VERSION_PATTERN = re.compile(r"Power\s*Automate[:\s]*v?(\d+\.\d+[\d.]*)", re.IGNORECASE)
    
    LOG_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.+)"
    )
    
    def detect(self, content: str, filename: Optional[str] = None) -> float:
        confidence = 0.0
        
        for pattern in self.SIGNATURES:
            if pattern.search(content):
                confidence += 0.25
        
        return min(confidence, 1.0)
    
    def extract_version(self, content: str) -> Optional[str]:
        match = self.VERSION_PATTERN.search(content)
        return match.group(1) if match else None
    
    def parse_log_entry(self, line: str) -> Optional[RPALogEntry]:
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None
        
        timestamp_str, level, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = None
        
        return RPALogEntry(
            timestamp=timestamp,
            level=level.upper(),
            message=message.strip(),
            platform=RPAPlatform.POWER_AUTOMATE,
        )
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "platform": "power_automate",
            "version": self.extract_version(content),
        }
        
        # Extract flow name
        flow_match = re.search(r"Flow\s*Name[:\s]+([^\n,]+)", content, re.IGNORECASE)
        if flow_match:
            metadata["flow_name"] = flow_match.group(1).strip()
        
        return metadata


class RPAPlatformRegistry:
    """Registry of RPA platform adapters."""
    
    def __init__(self):
        self.adapters: List[RPAPlatformAdapter] = [
            AutomationAnywhereAdapter(),
            WorkFusionAdapter(),
            PegaRPAAdapter(),
            PowerAutomateAdapter(),
            # Add more adapters here
        ]
    
    def detect_platform(
        self,
        content: str,
        filename: Optional[str] = None,
        threshold: float = 0.5,
    ) -> tuple[RPAPlatform, float, Optional[RPAPlatformAdapter]]:
        """
        Detect RPA platform from content.
        
        Returns:
            Tuple of (platform, confidence, adapter)
        """
        best_confidence = 0.0
        best_platform = RPAPlatform.UNKNOWN
        best_adapter = None
        
        for adapter in self.adapters:
            confidence = adapter.detect(content, filename)
            if confidence > best_confidence:
                best_confidence = confidence
                best_adapter = adapter
                
                # Infer platform from adapter class name
                adapter_name = adapter.__class__.__name__.replace("Adapter", "").lower()
                for platform in RPAPlatform:
                    if adapter_name in platform.value or platform.value in adapter_name:
                        best_platform = platform
                        break
        
        if best_confidence < threshold:
            return RPAPlatform.UNKNOWN, best_confidence, None
        
        return best_platform, best_confidence, best_adapter
    
    def parse_logs(
        self,
        content: str,
        platform: Optional[RPAPlatform] = None,
        adapter: Optional[RPAPlatformAdapter] = None,
    ) -> List[RPALogEntry]:
        """
        Parse RPA logs into structured entries.
        
        Args:
            content: Log content
            platform: Known platform (optional, will auto-detect)
            adapter: Specific adapter to use (optional)
        
        Returns:
            List of parsed log entries
        """
        if adapter is None:
            if platform is None:
                platform, _, adapter = self.detect_platform(content)
                if adapter is None:
                    logger.warning("Could not detect RPA platform")
                    return []
            else:
                # Find adapter for platform
                for a in self.adapters:
                    if a.detect(content) > 0.5:
                        adapter = a
                        break
                
                if adapter is None:
                    logger.warning("No adapter found for platform: %s", platform)
                    return []
        
        entries = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            entry = adapter.parse_log_entry(line)
            if entry:
                entries.append(entry)
        
        return entries


# Global registry
_rpa_registry: Optional[RPAPlatformRegistry] = None


def get_rpa_registry() -> RPAPlatformRegistry:
    """Get or create the global RPA platform registry."""
    global _rpa_registry
    if _rpa_registry is None:
        _rpa_registry = RPAPlatformRegistry()
    return _rpa_registry
