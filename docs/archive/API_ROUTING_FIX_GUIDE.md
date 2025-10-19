# API Routing Fix - Troubleshooting Guide

## Problem
All API endpoints returning 404 Not Found despite containers running healthy.

## Quick Diagnosis Commands

```bash
# 1. Check if API is responding at all
wsl docker exec -it rca_core curl -v http://localhost:8000/

# 2. Check FastAPI app routes
wsl docker exec -it rca_core python -c "from apps.api.main import app; import json; print(json.dumps([{'path': r.path, 'name': r.name} for r in app.routes], indent=2))"

# 3. Check if routers are imported
wsl docker exec -it rca_core python -c "from apps.api.main import app; print(app.router)"

# 4. Test health endpoint directly
wsl docker exec -it rca_core curl http://localhost:8000/api/health/live

# 5. Check gunicorn process
wsl docker exec -it rca_core ps aux | grep gunicorn

# 6. Check environment variables
wsl docker exec -it rca_core env | grep -E "POSTGRES|JWT|OLLAMA"
```

## Common Causes & Fixes

### 1. Router Not Mounted Correctly
**Check:** Is the router included with correct prefix?
```python
# In main.py, should see:
app.include_router(health.router, prefix="/api/health", tags=["health"])
```

**Fix:** Verify all routers are imported and included

### 2. Async/Await Issues
**Symptom:** Routes exist but don't execute  
**Fix:** Ensure all endpoints are properly async or sync

### 3. Middleware Blocking
**Check:** Security middleware might be rejecting requests  
**Fix:** Temporarily disable middleware to test

### 4. Gunicorn vs Uvicorn
**Issue:** Gunicorn might not be passing requests correctly  
**Test:** Try running with uvicorn directly

```bash
# Stop current container
wsl docker stop rca_core

# Run with uvicorn directly
wsl docker run -it --rm \
  --network rca_network \
  -p 8000:8000 \
  docker-rca_core \
  uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### 5. Path Prefix Issue
**Check:** Are routes registered with wrong prefix?  
**Symptom:** `/api/health/live` → 404, but `/health/live` works

**Fix:** Adjust router prefixes in main.py

### 6. CORS Configuration
**Check:** CORS middleware might be blocking  
**Test:** Make request with explicit origin header

```bash
curl -H "Origin: http://localhost:3000" http://localhost:8000/api/health/live
```

## Step-by-Step Debug Process

### Step 1: Verify Container Health
```bash
wsl docker ps
# Confirm rca_core is running and healthy
```

### Step 2: Check Logs for Startup Errors
```bash
wsl docker logs rca_core | grep -i error
wsl docker logs rca_core | grep -i exception
```

### Step 3: Exec Into Container
```bash
wsl docker exec -it rca_core bash
```

### Step 4: Test Internally
```bash
# Inside container:
curl http://localhost:8000/api/health/live
curl http://localhost:8000/api/jobs
curl http://localhost:8000/docs
```

### Step 5: Check Python Import
```bash
# Inside container:
python3 << EOF
from apps.api.main import app
print(f"Routes: {len(app.routes)}")
for route in app.routes:
    print(f"  {route.path} -> {route.name}")
EOF
```

### Step 6: Test with Python Requests
```bash
# Inside container:
python3 << EOF
import requests
response = requests.get('http://localhost:8000/api/health/live')
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
EOF
```

## Alternative: Run Backend Locally (Without Docker)

If Docker issues persist, run backend directly on Windows:

### 1. Install Dependencies
```powershell
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
pip install --upgrade pydantic "pydantic[email]>=2.0"
pip install -r requirements.txt
```

### 2. Set Environment Variables
```powershell
$env:PYTHONPATH = "$PWD"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "15432"
$env:POSTGRES_USER = "rca_user"
$env:POSTGRES_PASSWORD = "your_password"
$env:POSTGRES_DB = "rca_engine"
$env:JWT_SECRET_KEY = "your-secret-key-here-change-in-production"
$env:OLLAMA_HOST = "http://localhost:11435"
$env:DEBUG = "true"
```

### 3. Run with Uvicorn
```powershell
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test
```powershell
curl http://localhost:8000/api/health/live
```

## Quick Fix: Simplified Test Endpoint

If all else fails, add a simple test endpoint to verify routing works:

### 1. Edit main.py
```python
# Add this RIGHT AFTER creating the FastAPI app
@app.get("/test")
async def test_endpoint():
    return {"status": "working", "message": "Test endpoint is accessible"}
```

### 2. Restart Container
```bash
wsl docker restart rca_core
```

### 3. Test
```bash
curl http://localhost:8000/test
```

If this works, the issue is with router registration, not basic routing.

## Expected Working Response

When fixed, you should see:

```bash
$ curl http://localhost:8000/api/health/live
{"status":"ok","app":"RCA Engine","version":"1.0.0"}

$ curl http://localhost:8000/api/jobs
{"jobs":[]}  # or 401 if auth required

$ curl http://localhost:8000/docs
# HTML page with Swagger UI
```

## Contact Information

If issue persists after these steps, provide:
1. Full output of `wsl docker logs rca_core`
2. Output of route listing command
3. Contents of `apps/api/main.py` (first 200 lines)
4. Gunicorn/Uvicorn configuration
5. Docker compose file

---

**Last Updated:** October 13, 2025  
**Purpose:** Unblock full E2E integration testing
