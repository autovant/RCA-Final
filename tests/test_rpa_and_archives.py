"""Tests for RPA adapters and enhanced archive extractors."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from core.files.rpa_adapters import (
    RPAPlatformAdapter,
    AutomationAnywhereAdapter,
    WorkFusionAdapter,
    PegaRPAAdapter,
    PowerAutomateAdapter,
    RPAPlatformRegistry,
)
from core.files.enhanced_archives import (
    ArchiveExtractor,
    SevenZipExtractor,
    RarExtractor,
    ISOExtractor,
    EnhancedArchiveExtractor,
)


class TestAutomationAnywhereAdapter:
    """Test suite for Automation Anywhere adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return AutomationAnywhereAdapter()
    
    def test_detect_valid_log(self, adapter):
        """Test detecting valid Automation Anywhere log."""
        log_content = """
[2024-01-15 10:30:00] INFO [Bot Runner] Starting bot execution
[2024-01-15 10:30:01] DEBUG [Bot Runner] Variable initialized: counter = 0
"""
        confidence = adapter.detect(log_content)
        assert confidence > 0.0  # Returns confidence score
    
    def test_detect_invalid_log(self, adapter):
        """Test detecting non-AA log."""
        confidence = adapter.detect("Random log content")
        assert confidence == 0.0  # No match returns 0.0
    
    def test_parse_log_entries(self, adapter):
        """Test parsing log entries."""
        log_content = """
[2024-01-15 10:30:00] INFO [Bot Runner] Starting bot execution
[2024-01-15 10:30:05] ERROR [Bot Runner] Failed to click element
[2024-01-15 10:30:06] INFO [Bot Runner] Execution completed
"""
        entries = adapter.parse_logs(log_content)
        
        assert len(entries) == 3
        assert entries[0]["level"] == "INFO"
        assert "Starting bot execution" in entries[0]["message"]
        assert entries[1]["level"] == "ERROR"


class TestWorkFusionAdapter:
    """Test suite for WorkFusion adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return WorkFusionAdapter()
    
    def test_detect_valid_log(self, adapter):
        """Test detecting valid WorkFusion log."""
        log_content = """
2024-01-15T10:30:00.123Z [WorkFusion] [INFO] Starting RPA process
2024-01-15T10:30:01.456Z [WorkFusion] [DEBUG] Processing record 1
"""
        confidence = adapter.detect(log_content)
        assert confidence > 0.0
    
    def test_parse_with_transaction_id(self, adapter):
        """Test parsing with transaction tracking."""
        log_content = """
2024-01-15T10:30:00.123Z [WorkFusion] [INFO] Transaction TX123 started
2024-01-15T10:30:05.789Z [WorkFusion] [ERROR] Transaction TX123 failed
"""
        entries = adapter.parse_logs(log_content)
        
        assert len(entries) == 2
        assert entries[0]["transaction_id"] == "TX123"
        assert entries[1]["transaction_id"] == "TX123"


class TestPegaRPAAdapter:
    """Test suite for Pega RPA adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return PegaRPAAdapter()
    
    def test_detect_valid_log(self, adapter):
        """Test detecting valid Pega log."""
        log_content = """
[Pega Robot Runtime] 2024-01-15 10:30:00 INFO: Automation started
[Pega Robot Runtime] 2024-01-15 10:30:01 DEBUG: Variable set: status=processing
"""
        confidence = adapter.detect(log_content)
        assert confidence > 0.0
    
    def test_parse_with_automation_id(self, adapter):
        """Test parsing with automation tracking."""
        log_content = """
[Pega Robot Runtime] 2024-01-15 10:30:00 INFO: Automation AUTO456 started
[Pega Robot Runtime] 2024-01-15 10:30:05 ERROR: Automation AUTO456 failed
"""
        entries = adapter.parse_logs(log_content)
        
        assert len(entries) == 2
        assert entries[0]["automation_id"] == "AUTO456"


class TestPowerAutomateAdapter:
    """Test suite for Power Automate adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return PowerAutomateAdapter()
    
    def test_detect_valid_log(self, adapter):
        """Test detecting valid Power Automate log."""
        log_content = """
{"timestamp":"2024-01-15T10:30:00Z","level":"Information","message":"Flow started","flowId":"flow123"}
{"timestamp":"2024-01-15T10:30:05Z","level":"Error","message":"Action failed","flowId":"flow123"}
"""
        confidence = adapter.detect(log_content)
        assert confidence > 0.0
    
    def test_parse_json_logs(self, adapter):
        """Test parsing JSON-formatted logs."""
        log_content = """
{"timestamp":"2024-01-15T10:30:00Z","level":"Information","message":"Flow started","flowId":"flow123"}
{"timestamp":"2024-01-15T10:30:01Z","level":"Warning","message":"Retry attempted","flowId":"flow123","runId":"run456"}
"""
        entries = adapter.parse_logs(log_content)
        
        assert len(entries) == 2
        assert entries[0]["level"] == "Information"
        assert entries[0]["flow_id"] == "flow123"
        assert entries[1]["run_id"] == "run456"


class TestRPAPlatformRegistry:
    """Test suite for RPA platform registry."""
    
    @pytest.fixture
    def registry(self):
        """Create registry instance."""
        return RPAPlatformRegistry()
    
    def test_detect_automation_anywhere(self, registry):
        """Test detecting Automation Anywhere logs."""
        log_content = "[2024-01-15] INFO [Bot Runner] Starting"
        
        platform = registry.detect_platform(log_content)
        assert platform is not None
        assert platform.platform == "automation_anywhere"
    
    def test_detect_workfusion(self, registry):
        """Test detecting WorkFusion logs."""
        log_content = "2024-01-15T10:30:00Z [WorkFusion] [INFO] Starting"
        
        platform = registry.detect_platform(log_content)
        assert platform is not None
        assert platform.platform == "workfusion"
    
    def test_detect_pega(self, registry):
        """Test detecting Pega logs."""
        log_content = "[Pega Robot Runtime] 2024-01-15 INFO: Starting"
        
        platform = registry.detect_platform(log_content)
        assert platform is not None
        assert platform.platform == "pega_rpa"
    
    def test_detect_power_automate(self, registry):
        """Test detecting Power Automate logs."""
        log_content = '{"timestamp":"2024-01-15","level":"Info","flowId":"123"}'
        
        platform = registry.detect_platform(log_content)
        assert platform is not None
        assert platform.platform == "power_automate"
    
    def test_detect_unknown(self, registry):
        """Test detecting unknown platform."""
        log_content = "Random log content without RPA markers"
        
        platform = registry.detect_platform(log_content)
        assert platform is None
    
    def test_parse_logs(self, registry):
        """Test parsing logs with detected platform."""
        log_content = "[2024-01-15] INFO [Bot Runner] Starting bot"
        
        entries = registry.parse_logs(log_content)
        assert len(entries) > 0
        assert "timestamp" in entries[0]


class TestSevenZipExtractor:
    """Test suite for 7z extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return SevenZipExtractor()
    
    @pytest.mark.asyncio
    async def test_can_handle_7z(self, extractor):
        """Test 7z format detection."""
        assert await extractor.can_handle(Path("test.7z")) is True
        assert await extractor.can_handle(Path("test.zip")) is False
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_extract_7z(self, mock_run, extractor, tmp_path):
        """Test extracting 7z archive."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Everything is Ok")
        
        archive_path = tmp_path / "test.7z"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = await extractor.extract(archive_path, output_dir)
        
        assert result["success"] is True
        assert "file_count" in result
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_extract_failure(self, mock_run, extractor, tmp_path):
        """Test extraction failure handling."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        
        archive_path = tmp_path / "test.7z"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = await extractor.extract(archive_path, output_dir)
        
        assert result["success"] is False
        assert "error" in result


class TestRarExtractor:
    """Test suite for RAR extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return RarExtractor()
    
    @pytest.mark.asyncio
    async def test_can_handle_rar(self, extractor):
        """Test RAR format detection."""
        assert await extractor.can_handle(Path("test.rar")) is True
        assert await extractor.can_handle(Path("test.zip")) is False
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_extract_rar(self, mock_run, extractor, tmp_path):
        """Test extracting RAR archive."""
        mock_run.return_value = MagicMock(returncode=0, stdout="All OK")
        
        archive_path = tmp_path / "test.rar"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = await extractor.extract(archive_path, output_dir)
        
        assert result["success"] is True


class TestISOExtractor:
    """Test suite for ISO extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ISOExtractor()
    
    @pytest.mark.asyncio
    async def test_can_handle_iso(self, extractor):
        """Test ISO format detection."""
        assert await extractor.can_handle(Path("test.iso")) is True
        assert await extractor.can_handle(Path("test.img")) is True
        assert await extractor.can_handle(Path("test.zip")) is False
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_extract_iso(self, mock_run, extractor, tmp_path):
        """Test extracting ISO image."""
        mock_run.return_value = MagicMock(returncode=0)
        
        archive_path = tmp_path / "test.iso"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = await extractor.extract(archive_path, output_dir)
        
        assert result["success"] is True


class TestEnhancedArchiveExtractor:
    """Test suite for unified archive extractor."""
    
    @pytest.mark.asyncio
    async def test_extract_7z(self, tmp_path):
        """Test extracting 7z via unified interface."""
        archive_path = tmp_path / "test.7z"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK")
            
            result = await EnhancedArchiveExtractor.extract(
                archive_path,
                output_dir
            )
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_rar(self, tmp_path):
        """Test extracting RAR via unified interface."""
        archive_path = tmp_path / "test.rar"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = await EnhancedArchiveExtractor.extract(
                archive_path,
                output_dir
            )
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_iso(self, tmp_path):
        """Test extracting ISO via unified interface."""
        archive_path = tmp_path / "test.iso"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = await EnhancedArchiveExtractor.extract(
                archive_path,
                output_dir
            )
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self, tmp_path):
        """Test handling unsupported format."""
        archive_path = tmp_path / "test.unknown"
        archive_path.touch()
        
        output_dir = tmp_path / "output"
        
        result = await EnhancedArchiveExtractor.extract(
            archive_path,
            output_dir
        )
        
        assert result["success"] is False
        assert "Unsupported" in result.get("error", "")
