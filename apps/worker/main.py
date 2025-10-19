"""
RCA Engine Worker Application
Worker process for handling long-running RCA analysis jobs.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from uuid import uuid4

from core.config import settings
from core.db.database import init_db, close_db
from core.jobs.service import JobService
from core.jobs.processor import JobProcessor
from core.logging import setup_logging
from core.metrics import setup_metrics

from apps.worker.events import emit_fingerprint_status

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class Worker:
    """RCA Engine Worker for processing analysis jobs."""
    
    def __init__(self):
        self.running = True
        self.job_service = JobService()
        self.job_processor = JobProcessor(self.job_service)
        # Generate a stable identifier without relying on a running event loop
        self.worker_id = f"worker_{uuid4().hex}"
        
    async def start(self):
        """Start the worker."""
        logger.info(f"Starting RCA Engine Worker: {self.worker_id}")
        
        # Initialize database
        await init_db()
        
        # Setup metrics
        setup_metrics()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        try:
            await self._run_worker_loop()
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the worker."""
        logger.info(f"Stopping RCA Engine Worker: {self.worker_id}")
        self.running = False
        await self.job_processor.close()
        await close_db()
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    async def _run_worker_loop(self):
        """Main worker loop for processing jobs."""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Poll for pending jobs
                job = await self.job_service.get_next_pending_job()
                
                if job:
                    logger.info(f"Processing job: {job.id}")
                    await self.job_service.create_job_event(
                        job.id,
                        "worker-assigned",
                        {"worker_id": self.worker_id},
                    )
                    await self._process_job(job)
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(settings.WORKER_POLL_INTERVAL)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                # Wait before retrying to avoid tight error loops
                await asyncio.sleep(5)
    
    async def _process_job(self, job):
        """Process a single job."""
        try:
            # Process the job based on type
            if job.job_type == "rca_analysis":
                result = await self.job_processor.process_rca_analysis(job)
            elif job.job_type == "log_analysis":
                result = await self.job_processor.process_log_analysis(job)
            elif job.job_type == "embedding_generation":
                result = await self.job_processor.process_embedding_generation(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Update job with results
            await self.job_service.complete_job(job.id, result)

            try:
                await emit_fingerprint_status(
                    self.job_service,
                    str(job.id),
                    result.get("fingerprint"),
                    job_type=str(job.job_type),
                )
            except Exception:  # pragma: no cover - telemetry must not block job completion
                logger.exception("Failed to emit fingerprint status telemetry for job %s", job.id)
            
            logger.info(f"Job completed successfully: {job.id}")
            
        except Exception as e:
            logger.error(f"Job processing failed: {job.id}, error: {e}", exc_info=True)
            await self.job_service.fail_job(job.id, str(e))


async def main():
    """Main worker entry point."""
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed to start: {e}", exc_info=True)
        sys.exit(1)

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        # Don't call sys.exit here - let the worker loop finish naturally
        # to ensure proper cleanup via the finally block in start()
