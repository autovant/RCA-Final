# Draft Status Fix Applied

## ✅ Issue Resolved

**Problem:** File upload was failing with `ValueError: Invalid status: draft`

**Root Cause:** The `Job` model's status validator and database CHECK constraint did not include `"draft"` as a valid status.

## Changes Made

### 1. Updated Job Model (`core/db/models.py`)
- **Line 98:** Added `'draft'` to database CHECK constraint
- **Line 105:** Added `"draft"` to Python validator allowed set

```python
# Before:
allowed = {"pending", "running", "completed", "failed", "cancelled"}

# After:
allowed = {"draft", "pending", "running", "completed", "failed", "cancelled"}
```

### 2. Database Migration (`alembic/versions/add_draft_status.py`)
- Created migration to update PostgreSQL CHECK constraint
- Ran migration successfully: `alembic upgrade head`
- Migration output: `Running upgrade 6f5ba0b2cc91 -> add_draft_status`

## Status

✅ **Model updated** - Job model now accepts "draft" status  
✅ **Database updated** - CHECK constraint allows "draft" values  
✅ **Backend running** - Uvicorn auto-reloaded with changes  
✅ **Ready for testing** - File upload should now work

## Test Now

Upload a file via UI at http://localhost:3000 and verify:
- No `ValueError: Invalid status: draft` error
- Job created with status='draft'
- File attaches successfully
- Status transitions to 'pending' after file upload
- Worker picks up job and processes it

## Job Status Flow

```
draft (new, invisible to worker)
  ↓ (after file attachment completes)
pending (visible to worker, ready for processing)
  ↓ (worker picks up job)
running (worker processing)
  ↓ (on success)
completed
```

---

**Time:** 2025-10-17 4:47 PM  
**Files Modified:** 
- `core/db/models.py`
- `alembic/versions/add_draft_status.py`
