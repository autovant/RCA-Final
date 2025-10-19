# File Upload Race Condition - DIAGNOSIS

**Date**: October 17, 2025  
**Issue**: Files uploading but jobs failing with "No files uploaded for analysis"  
**Status**: ⚠️ RACE CONDITION IDENTIFIED

## Problem Identified

### Symptom
User uploads file, but:
- Job created with `status='pending'` and **0 files**
- Worker picks it up immediately (< 5 seconds)
- Worker fails: "No files uploaded for analysis"
- No progress updates shown

### Recent Job History
```
4:09:24 PM - Job b0907871... : FAILED (0 files)
4:09:22 PM - Job eaa06b8e... : COMPLETED (1 file) ✓
4:00:59 PM - Job e04bd978... : FAILED (0 files)
4:00:57 PM - Job 5ddf0676... : COMPLETED (1 file) ✓
3:53:19 PM - Job da591cc9... : FAILED (0 files)
3:53:17 PM - Job 8c24d696... : COMPLETED (1 file) ✓
```

**Pattern**: Every upload creates TWO jobs - one succeeds, one fails!

## Root Cause Analysis

### Current Upload Flow

**Option 1: File Upload Creates Job** (`/api/files/upload` without job_id):
```
1. POST /api/files/upload (no job_id)
2. Backend creates Job with status='pending', files=[]
3. Job immediately visible to worker
4. Worker picks up job (< 5 seconds)
5. Worker checks for files → finds 0 files
6. Worker fails job: "No files uploaded"
7. File attachment happens (too late!)
```

**Option 2: UI Creates Job First**:
```
1. UI creates Job via POST /api/jobs
2. Job created with status='pending'
3. Worker picks it up immediately
4. UI uploads file to /api/files/upload?job_id=...
5. Worker already processing → finds no files → fails
```

### Code Evidence

**File Upload Endpoint** (`apps/api/routers/files.py:155`):
```python
if job_id is None:
    # Creates job with status="pending" immediately
    job_obj = Job(
        status="pending",  # ← Worker can see this immediately!
        input_manifest={"files": []},  # ← No files yet!
    )
    db.add(job_obj)
    await db.flush()  # ← Committed to DB
    # File attachment happens later in the function
```

**Worker Polling** (every 5 seconds):
```sql
SELECT * FROM jobs 
WHERE status = 'pending' 
ORDER BY priority DESC, created_at ASC
LIMIT 1
```

**Problem**: Job becomes visible to worker BEFORE file is attached!

## Why Progress Updates Don't Appear

1. Job created with `status='pending'`
2. Worker picks it up in < 5 seconds
3. Worker finds no files, fails immediately
4. **No progress events emitted** (job never actually starts processing)
5. UI shows no updates (EventSource never receives events)

## Solutions

### Solution 1: Use 'draft' Status (RECOMMENDED)

**Modify file upload to create jobs in 'draft' status**:

```python
# apps/api/routers/files.py
job_obj = Job(
    status="draft",  # ← Worker ignores draft jobs
    # ... rest of config
)
# After file is attached:
job_obj.status = "pending"  # ← Now worker can see it
await db.commit()
```

**Worker query stays the same** (only picks up 'pending' jobs).

### Solution 2: Atomic File Attachment

Keep job creation but ensure file attachment happens in same transaction:

```python
async with db.begin():
    job_obj = Job(status="pending", ...)
    db.add(job_obj)
    await db.flush()  # Get job ID
    
    # Attach file in SAME transaction
    file_obj = await file_service.ingest_upload(...)
    
    # Both committed atomically
    await db.commit()
```

### Solution 3: Delay Worker Pickup

Add a grace period:

```sql
SELECT * FROM jobs
WHERE status = 'pending'
  AND created_at < NOW() - INTERVAL '10 seconds'  -- Grace period
ORDER BY priority DESC
```

**Downside**: Adds artificial delay to all jobs.

### Solution 4: Two-Phase Upload (UI Changes)

Change UI flow:
```
1. Upload file first (no job creation)
2. Get file_id from upload response
3. Create job with file_ids=[...]
4. Job created with files already attached
```

**Downside**: Requires UI changes.

## Recommended Fix

**Implement Solution 1** (draft status):

### Changes Needed

1. **apps/api/routers/files.py** (line 155):
   ```python
   job_obj = Job(
       job_type="rca_analysis",
       user_id=str(current_user.id),
       input_manifest={"files": []},
       provider=default_provider,
       model=default_model,
       priority=0,
       status="draft",  # ← Change from "pending" to "draft"
       source={...},
   )
   ```

2. **apps/api/routers/files.py** (after file attachment, ~line 200):
   ```python
   # After file is successfully attached
   if job_obj.status == "draft":
       job_obj.status = "pending"
       await db.commit()
       await job_service.create_job_event(
           job_id_str,
           "ready",
           {"files_attached": 1},
           session=db,
       )
   ```

3. **Worker stays unchanged** - already only picks up 'pending' jobs

### Testing

After fix:
```
1. Upload file
2. Job created with status='draft'
3. File attached
4. Job status → 'pending'
5. Worker picks it up (now has files!)
6. Processing starts
7. Progress events emitted ✓
```

## Immediate Workaround

For now, when uploading:
1. **Expect the first job to fail** - this is the race condition
2. **Look for the SECOND job** (created 2 seconds later) - this one usually succeeds
3. Check `/api/jobs` and find the most recent COMPLETED job

Or just **retry the upload** - the second attempt often works because timing is different.

## Files to Modify

1. `apps/api/routers/files.py` - Add draft status logic
2. `core/db/models.py` - Verify status field allows 'draft' (likely already does)
3. Optional: Add migration to document 'draft' as valid status

## Testing Script

```powershell
# After implementing fix, test with:
$file = Get-Item "test.log"
$form = @{
    file = $file
}
$response = Invoke-RestMethod -Uri "http://localhost:8001/api/files/upload" -Method POST -Form $form
$jobId = $response.job_id

# Wait a moment
Start-Sleep -Seconds 2

# Check job status
Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$jobId" | Select status, @{N='files';E={$_.input_manifest.files.Count}}

# Should show: status=pending, files=1 (not 0!)
```

## Status

🔴 **BUG CONFIRMED**: Race condition between job creation and file attachment  
⚠️ **IMPACT**: Every upload fails first, may succeed on retry  
✅ **FIX IDENTIFIED**: Use 'draft' status until file is attached  
⏳ **IMPLEMENTATION**: Pending code changes

Would you like me to implement the fix?
