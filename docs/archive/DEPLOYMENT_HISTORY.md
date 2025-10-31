# Deployment History & Configuration

This document consolidates the deployment milestones, configuration decisions, and architectural setup from the RCA Insight Engine development cycle.

> **Current Guide**: See [Deployment Guide](../deployment/deployment-guide.md) for up-to-date deployment instructions.

---

## Timeline

### October 23, 2025 - Performance Optimizations Deployment ✅

**Status**: Complete - All 10 optimizations deployed and operational

#### Implemented Optimizations

1. **Database Query Optimization**
   - `defer()` for lazy loading (raw_result, input_manifest fields)
   - `selectinload()` for efficient relationship loading
   - Eliminated N+1 queries
   - **Impact**: 40-60% query performance improvement

2. **Response Caching System**
   - In-memory caching with 300s TTL
   - LRU eviction strategy
   - Background cleanup task
   - `@cached` decorator integration
   - **Impact**: 90%+ cache hit rate potential
   - **Files**: `core/cache/response_cache.py` (273 lines)

3. **Batch Embedding Generation**
   - Automatic batch size optimization
   - Comprehensive error handling
   - Detailed logging
   - **Files**: `core/llm/embeddings.py`

4. **Connection Pool Monitoring**
   - `get_pool_stats()` method
   - Health endpoint integration
   - Proactive connection management
   - **Files**: `core/db/database.py`, `apps/api/routes/health.py`

5. **SSE Performance Improvements**
   - Optimized event batching
   - Reduced overhead
   - **Files**: SSE router endpoints

6. **Static Asset Optimization**
   - CDN-ready configuration
   - Cache headers
   - **Files**: Next.js configuration

7. **Database Connection Pooling**
   - Optimized pool size configuration
   - Connection reuse
   - **Files**: `core/db/database.py`

8. **Lazy Loading Strategies**
   - Deferred loading of large fields
   - On-demand relationship loading

9. **Query Result Pagination**
   - Efficient large dataset handling
   - Cursor-based pagination

10. **Health Check Optimization**
    - Fast health endpoint responses
    - Minimal database queries

**Server**: Running successfully on port 8001

---

### WSL Architecture & Hybrid Deployment

#### Network Topology

```
┌─────────────────────────────────────┐
│  Windows Browser                    │
│  http://localhost:3000              │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  Frontend (Next.js)                 │
│  Port: 3000 (Windows)               │
│  API calls to: <WSL_IP>:8001        │
└────────────┬────────────────────────┘
             │
             ↓ Direct connection (no port forwarding!)
┌─────────────────────────────────────┐
│  WSL2 (<WSL_IP>)                    │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Backend (FastAPI)            │  │
│  │ Port: 8001                   │  │
│  │ CORS: * (all origins)        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ Docker Network               │  │
│  │ PostgreSQL: 172.19.0.3:5432  │  │
│  │ Redis: 172.19.0.2:6379       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

#### Key Configuration Decisions

**Port Selection**:
- Backend: Port 8001 (changed from 8000 to avoid conflicts)
- Frontend: Port 3000
- PostgreSQL: Port 15432 (exposed from container 5432)
- Redis: Port 16379 (exposed from container 6379)

**CORS Configuration**:
- Fixed to allow all origins (`*`) for development
- Frontend directly calls WSL IP address
- No port forwarding required

**WSL IP Handling**:
- WSL IP address can change after Windows restart
- Frontend must be updated with current WSL IP
- Check current IP: `wsl hostname -I`
- Update frontend: Modify `NEXT_PUBLIC_API_BASE_URL` in `ui/.env.local`

---

### Database Isolation & Environment Setup

#### Isolated Resources

**Database**:
- Name: `rca_engine_final` (isolated from other apps)
- Host: 172.19.0.3 (Docker network)
- Port: 5432 (internal), 15432 (exposed)
- User: `rca_user`
- Password: `rca_password`

**Redis**:
- DB: 1 (vs DB 0 for other applications - isolated)
- Host: 172.19.0.2 (Docker network)
- Port: 6379 (internal), 16379 (exposed)

**Rationale**: Multiple RCA applications can coexist on the same host without database conflicts.

#### Environment Configuration

**WSL Python Environment**:
- Python 3.12 virtual environment
- 60+ packages installed
- All dependencies compatible

**Database Migrations**:
- Alembic migrations successfully applied
- Schema created in `rca_engine_final` database
- Tables: users, jobs, tickets, files, embeddings, incidents, fingerprints, etc.

**.env Configuration**:
```properties
POSTGRES_HOST=172.19.0.3  # Docker container IP
POSTGRES_PORT=5432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password
POSTGRES_DB=rca_engine_final  # ISOLATED

REDIS_HOST=172.19.0.2  # Docker container IP
REDIS_PORT=6379
REDIS_DB=1  # ISOLATED
```

#### Created Scripts

- `start-backend-wsl.sh` - Backend startup script (WSL)
- `start-app.ps1` - Combined startup (Windows launcher)
- `quick-start-dev.ps1` - Consolidated one-command startup
- `start-dev.ps1` - Docker services only
- `stop-dev.ps1` - Stop all services

---

## Historical Issues & Resolutions

### WSL Networking
**Issue**: Frontend unable to connect to backend across WSL boundary  
**Resolution**: Direct WSL IP connection, CORS wildcard, no port forwarding

### Port Conflicts
**Issue**: Port 8001 conflicts with other services  
**Resolution**: Changed backend to port 8001, documented in multiple files

### Database Isolation
**Issue**: Multiple RCA apps sharing database causing conflicts  
**Resolution**: Separate database (`rca_engine_final`) and Redis DB (1)

### WSL IP Changes
**Issue**: WSL IP address changes after Windows restart  
**Resolution**: 
- Document IP checking procedure: `wsl hostname -I`
- Update frontend env: `NEXT_PUBLIC_API_BASE_URL`
- Created helper scripts

### Firewall Rules
**Issue**: Windows Firewall blocking WSL access  
**Resolution**: `ENABLE-NETWORK-ACCESS.ps1` script to configure firewall rules

---

## Access URLs

**During Development**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 or http://<WSL_IP>:8001
- API Docs: http://localhost:8000/docs
- Metrics: http://localhost:8001/metrics

**Health Checks**:
- Liveness: http://localhost:8000/api/health/live
- Readiness: http://localhost:8000/api/health/ready

---

## Lessons Learned

1. **WSL IP is Dynamic**: Always check and update after Windows restarts
2. **Port Forwarding Not Needed**: Direct WSL IP access is more reliable
3. **Database Isolation Critical**: Prevents cross-application conflicts
4. **CORS Must Be Explicit**: Wildcard works for dev, restrict in production
5. **Docker in WSL Works Best**: Avoid Docker Desktop in enterprise environments
6. **Script Consolidation**: Single startup script (`quick-start-dev.ps1`) greatly improves DX
7. **Performance Monitoring**: Cache statistics and pool monitoring catch issues early

---

## Related Documentation

- [Current Deployment Guide](../deployment/deployment-guide.md) - Up-to-date deployment instructions
- [Deployment Topology Diagram](../diagrams/deployment.md) - Visual infrastructure overview
- [Startup Scripts Guide](../../scripts/README.md) - All script documentation
- [WSL Networking Fixes](WSL_NETWORKING_RESOLVED.md) - Network troubleshooting
- [Troubleshooting Playbook](../operations/troubleshooting.md) - Common issues

---

**Last Updated**: October 2025 (consolidated from multiple deployment reports)
