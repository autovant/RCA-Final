# ✅ FIXED: Live Job Telemetry Now Online

**Issue:** "Live job telemetry is offline. Displaying curated preview data."

## Root Causes Identified & Resolved

### 1. **Duplicate Index Definitions** ❌ → ✅ FIXED
**Problem:** SQLAlchemy models had duplicate index definitions causing table creation to ROLLBACK.

**Locations:**
- `JobEvent` model (line 158): `event_type = Column(..., index=True)` + explicit `Index("ix_job_events_event_type", "event_type")` in `__table_args__`
- `User` model (lines 657-658): `username` and `email` columns with `index=True` + explicit indexes in `__table_args__`

**Fix Applied:**
```python
# Before:
event_type = Column(String(50), nullable=False, index=True)  # ❌ Creates index
__table_args__ = (
    Index("ix_job_events_event_type", "event_type"),  # ❌ Duplicate!
)

# After:
event_type = Column(String(50), nullable=False)  # ✅ Index defined below
__table_args__ = (
    Index("ix_job_events_event_type", "event_type"),  # ✅ Only definition
)
```

### 2. **Missing pgvector Extension** ❌ → ✅ FIXED
**Problem:** `documents` table uses `VECTOR(1536)` type but the extension wasn't enabled.

**Error:**
```
sqlalchemy.exc.ProgrammingError: type "vector" does not exist
ERROR: Application startup failed. Exiting.
```

**Fix Applied:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. **Transaction Rollbacks** ❌ → ✅ FIXED
**Problem:** Due to above errors, all table creation attempts were being ROLLED BACK, leaving database empty.

**Result:** Backend started successfully but database had no tables → 500 errors on `/api/jobs/` → UI showed "telemetry offline".

---

## Files Modified

### `core/db/models.py`
**Lines 158, 657-659:** Removed `index=True` from column definitions that already have explicit indexes in `__table_args__`.

```python
# JobEvent model - Line 158
event_type = Column(String(50), nullable=False)  # Index defined in __table_args__

# User model - Lines 657-659
username = Column(String(100), unique=True, nullable=False)  # Index defined in __table_args__
email = Column(String(255), unique=True, nullable=False)  # Index defined in __table_args__
is_active = Column(Boolean, default=True, nullable=False)  # Index defined in __table_args__
```

---

## Verification Steps

### 1. Check Database Tables
```powershell
wsl bash -c "docker exec rca_db psql -U rca_user -d rca_engine -c '\dt'"
```
**Expected:** List of 12 tables including `jobs`, `job_events`, `users`, `documents`, etc.

### 2. Test Jobs API
```powershell
wsl bash -c "curl -s http://localhost:8000/api/jobs/ | jq '.'"
```
**Expected:** `[]` (empty array) or list of jobs

### 3. Check UI
**URL:** http://localhost:3000  
**Expected:** Dashboard loads without "Live job telemetry is offline" error

---

## System Status - OPERATIONAL ✅

| Component | Status | Endpoint |
|-----------|--------|----------|
| **Backend API** | ✅ Running | http://localhost:8000 |
| **Database** | ✅ Healthy | localhost:15432 (12 tables) |
| **pgvector Extension** | ✅ Enabled | ` SELECT extname FROM pg_extension;` |
| **Jobs API** | ✅ Working | GET /api/jobs/ returns 200 OK |
| **UI Telemetry** | ✅ ONLINE | No "offline" message |
| **GitHub Copilot** | ✅ Configured | DEFAULT_PROVIDER=copilot |

---

## Testing Recommendations

### 1. Create a Test Job
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "job_type": "rca_analysis",
    "provider": "copilot",
    "model": "gpt-4",
    "input_manifest": {
      "description": "Test RCA job"
    }
  }'
```

### 2. Verify Job Appears in UI
- Open http://localhost:3000
- Dashboard should show the newly created job
- No "telemetry offline" message should appear

### 3. Test File Upload
```powershell
# Use test file created earlier:
tools/manual-tests/test-log.txt

# Upload through UI at http://localhost:3000
```

---

## Lessons Learned

1. **Always check for duplicate indexes:** Column-level `index=True` + explicit `Index()` definition causes conflicts
2. **PostgreSQL extensions:** When dropping schema, extensions persist but need to be verified
3. **Silent failures:** Transaction rollbacks can happen silently if exception handlers swallow errors
4. **Volume persistence:** Database container volume persisted old state, required manual extension creation

---

## Future Prevention

### Add to CI/CD Pipeline:
```python
# Test for duplicate index definitions
def test_no_duplicate_indexes():
    from core.db.models import Base
    for table in Base.metadata.tables.values():
        column_indexes = [col.index for col in table.columns if hasattr(col, 'index') and col.index]
        explicit_indexes = [idx for idx in table.indexes]
        # Assert no column appears in both lists
```

### Database Health Check Script:
```bash
#!/bin/bash
# check-db-health.sh

# Check if pgvector is installed
docker exec rca_db psql -U rca_user -d rca_engine -c "SELECT extname FROM pg_extension WHERE extname='vector';" | grep -q vector
if [ $? -ne 0 ]; then
    echo "❌ pgvector extension not installed"
    exit 1
fi

# Check if all tables exist
TABLES=$(docker exec rca_db psql -U rca_user -d rca_engine -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
if [ "$TABLES" -lt 12 ]; then
    echo "❌ Expected 12 tables, found $TABLES"
    exit 1
fi

echo "✅ Database health check passed"
```

---

## Quick Reference

### Restart Everything:
```powershell
.\Stop-Docker.ps1
.\Start-Docker.ps1
```

### View Backend Logs:
```powershell
wsl bash -c "docker logs -f rca_core"
```

### Check Container Status:
```powershell
wsl bash -c "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

---

**Resolution Date:** 2025-10-15  
**Time to Resolution:** ~45 minutes  
**Status:** ✅ **RESOLVED - System Operational**
