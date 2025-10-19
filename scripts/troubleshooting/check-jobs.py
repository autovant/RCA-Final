#!/usr/bin/env python
"""Quick diagnostic to check job statuses."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.database import get_session
from core.db.models import Job, File
from sqlalchemy import select, desc

async def check_jobs():
    async with get_session() as session:
        # Get recent jobs
        result = await session.execute(
            select(Job)
            .order_by(desc(Job.created_at))
            .limit(5)
        )
        jobs = result.scalars().all()
        
        print("\n=== Recent Jobs ===\n")
        for job in jobs:
            print(f"Job ID: {job.id}")
            print(f"  Status: {job.status}")
            print(f"  Created: {job.created_at}")
            print(f"  Error: {job.error_message or 'None'}")
            
            # Get files for this job
            files_result = await session.execute(
                select(File).where(File.job_id == str(job.id))
            )
            files = files_result.scalars().all()
            print(f"  Files: {len(files)}")
            for f in files:
                print(f"    - {f.original_filename} ({f.file_size} bytes)")
            print()

if __name__ == "__main__":
    asyncio.run(check_jobs())
