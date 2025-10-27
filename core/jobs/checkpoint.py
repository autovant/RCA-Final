"""
Job checkpoint system for resuming long-running analysis tasks.
Allows jobs to resume from the last successful stage on failure/restart.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles

from core.config import settings

logger = logging.getLogger(__name__)


class JobCheckpoint:
    """Manages checkpoints for job processing."""
    
    def __init__(self, job_id: str, checkpoint_dir: Optional[Path] = None):
        """
        Initialize checkpoint manager for a job.
        
        Args:
            job_id: Job identifier
            checkpoint_dir: Optional checkpoint directory (defaults to temp)
        """
        self.job_id = job_id
        self.checkpoint_dir = checkpoint_dir or Path("/tmp/rca_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{job_id}.json"
    
    async def save(self, stage: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Save a checkpoint for the current stage.
        
        Args:
            stage: Current processing stage (e.g., 'redaction', 'embedding', 'analysis')
            data: Optional additional data to save with checkpoint
        """
        try:
            checkpoint = {
                "job_id": self.job_id,
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {}
            }
            
            async with aiofiles.open(self.checkpoint_file, 'w') as f:
                await f.write(json.dumps(checkpoint, indent=2))
            
            logger.info(f"Checkpoint saved for job {self.job_id} at stage '{stage}'")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint for job {self.job_id}: {e}")
            # Don't raise - checkpoint failure shouldn't stop job processing
    
    async def load(self) -> Optional[Dict[str, Any]]:
        """
        Load the last checkpoint for this job.
        
        Returns:
            Checkpoint data if exists, None otherwise
        """
        try:
            if not self.checkpoint_file.exists():
                return None
            
            async with aiofiles.open(self.checkpoint_file, 'r') as f:
                content = await f.read()
                checkpoint = json.loads(content)
            
            logger.info(
                f"Checkpoint loaded for job {self.job_id} "
                f"(stage: {checkpoint.get('stage')}, "
                f"timestamp: {checkpoint.get('timestamp')})"
            )
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint for job {self.job_id}: {e}")
            return None
    
    async def clear(self) -> None:
        """Clear/delete the checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info(f"Checkpoint cleared for job {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to clear checkpoint for job {self.job_id}: {e}")
    
    def get_stage(self) -> Optional[str]:
        """
        Get the current checkpoint stage synchronously.
        
        Returns:
            Stage name if checkpoint exists, None otherwise
        """
        try:
            if not self.checkpoint_file.exists():
                return None
            
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                return checkpoint.get('stage')
        except Exception as e:
            logger.error(f"Failed to get checkpoint stage for job {self.job_id}: {e}")
            return None


class CheckpointManager:
    """Global checkpoint manager for managing multiple job checkpoints."""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = checkpoint_dir or Path("/tmp/rca_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def get_checkpoint(self, job_id: str) -> JobCheckpoint:
        """
        Get a checkpoint instance for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobCheckpoint instance
        """
        return JobCheckpoint(job_id, self.checkpoint_dir)
    
    async def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """
        Clean up old checkpoint files.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of checkpoints cleaned up
        """
        cleaned = 0
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(
                        checkpoint_file.stat().st_mtime,
                        tz=timezone.utc
                    )
                    
                    if mtime < cutoff_time:
                        checkpoint_file.unlink()
                        cleaned += 1
                        logger.debug(f"Cleaned up old checkpoint: {checkpoint_file.name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to cleanup checkpoint {checkpoint_file}: {e}")
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old checkpoint files")
            
        except Exception as e:
            logger.error(f"Error during checkpoint cleanup: {e}")
        
        return cleaned
    
    async def list_checkpoints(self) -> list[Dict[str, Any]]:
        """
        List all active checkpoints.
        
        Returns:
            List of checkpoint information
        """
        checkpoints = []
        try:
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    async with aiofiles.open(checkpoint_file, 'r') as f:
                        content = await f.read()
                        checkpoint = json.loads(content)
                        checkpoints.append(checkpoint)
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
        
        return checkpoints


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get the global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


__all__ = [
    "JobCheckpoint",
    "CheckpointManager",
    "get_checkpoint_manager",
]
