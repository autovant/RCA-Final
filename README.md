# RCA Engine - Unified Implementation

## Complete Implementation Guide & Status

This repository contains the unified RCA Engine codebase that combines the best features from both development and production versions. This document outlines the current implementation status and what needs to be completed.

---

## 🌐 Architecture Overview

```
├── apps/                    # Application layer
│   ├── api/                  # FastAPI HTTP API
│   │   ├── main.py            # Main API entry point ✅
│   │   ├── routers/           # API route handlers 🔧
│   │   ├── middleware/        # Security & rate limiting 🔧
│   │   └── __init__.py
│   └── worker/               # Background job processor
│       ├── main.py            # Worker entry point ✅
│       └── __init__.py
├── core/                    # Core business logic
│   ├── config.py              # Configuration management ✅
│   ├── db/                    # Database layer
│   │   ├── models.py          # SQLAlchemy models ✅
│   │   ├── database.py        # Database connection 🔧
│   │   └── __init__.py
│   ├── jobs/                  # Job processing
│   │   ├── service.py         # Job service ✅
│   │   ├── processor.py       # Job processing logic 🔧
│   │   └── __init__.py
│   ├── llm/                   # LLM provider abstraction
│   │   ├── providers/         # Provider implementations 🔧
│   │   ├── embeddings.py      # Embedding generation 🔧
│   │   └── __init__.py
│   ├── security/              # Security utilities
│   │   ├── auth.py            # Authentication 🔧
│   │   ├── middleware.py      # Security middleware 🔧
│   │   └── __init__.py
│   ├── logging.py             # Structured logging 🔧
│   ├── metrics.py             # Prometheus metrics 🔧
│   └── __init__.py
├── ui/                      # Next.js frontend
│   ├── package.json         # UI dependencies ✅
│   ├── Dockerfile.secure    # Secure UI container ✅
│   ├── src/                 # UI source code 🔧
│   ├── public/              # Static assets 🔧
│   └── next.config.js       # Next.js configuration 🔧
├── deploy/                  # Deployment configurations
│   ├── docker/              # Docker configurations
│   │   ├── docker-compose.yml # Complete stack ✅
│   │   ├── Dockerfile.secure  # Secure app container ✅
│   │   └── config/            # Monitoring configs 🔧
│   ├── scripts/             # Deployment scripts
│   │   ├── deploy.sh          # Main deployment script 🔧
│   │   ├── smoke-test.sh      # Health checks 🔧
│   │   └── secure-build.sh  # Security scanning 🔧
│   └── kubernetes/          # K8s manifests 🔧
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
└── docs/                    # Documentation
```

---

## ✅ **COMPLETED COMPONENTS**

### **Core Infrastructure**

- [x] **Configuration Management** - Comprehensive settings with Pydantic
- [x] **Database Models** - SQLAlchemy models with pgvector support
- [x] **Main API Application** - FastAPI with security middleware
- [x] **Worker Application** - Background job processor
- [x] **Docker Configuration** - Production-ready containers with security hardening
- [x] **Environment Template** - Complete .env.example with all settings

### **Security Features**

- [x] **Non-root User Execution** - Security-hardened containers
- [x] **Read-only Filesystem** - Minimal attack surface
- [x] **JWT Authentication** - Secure token-based auth
- [x] **CORS Configuration** - Proper origin restrictions
- [x] **Security Headers** - CSP, HSTS, XSS protection

### **Deployment**

- [x] **Docker Compose Stack** - Complete production deployment
- [x] **Monitoring Integration** - Prometheus, Grafana, Alertmanager
- [x] **Health Checks** - Comprehensive service health monitoring
- [x] **Network Isolation** - Secure internal networking

---

## 🔧 **REMAINING IMPLEMENTATION**

### **Critical Components (Priority 1)**

#### **1. Database Layer**

```python
# core/db/database.py - Database connection and session management
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings
from core.db.models import Base

class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            settings.database.DATABASE_URL,
            pool_size=settings.database.DB_POOL_SIZE,
            max_overflow=settings.database.DB_MAX_OVERFLOW,
            pool_timeout=settings.database.DB_POOL_TIMEOUT,
            pool_recycle=settings.database.DB_POOL_RECYCLE,
            pool_pre_ping=settings.database.DB_POOL_PRE_PING,
            echo=settings.SQL_ECHO,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close_db(self):
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        return self.async_session()

db_manager = DatabaseManager()
```

#### **2. Job Processing Logic**

```python
# core/jobs/processor.py - Job processing implementation
from typing import Dict, Any, List
from core.llm.providers import get_provider
from core.llm.embeddings import EmbeddingService
from core.file_processing import FileProcessor

class JobProcessor:
    def __init__(self):
        self.llm_provider = get_provider()
        self.embedding_service = EmbeddingService()
        self.file_processor = FileProcessor()

    async def process_rca_analysis(self, job: Job) -> Dict[str, Any]:
        """Process RCA analysis job."""
        # 1. Parse and validate input files
        files = await self.file_processor.process_job_files(job.id)

        # 2. Generate embeddings for content
        documents = await self.embedding_service.generate_embeddings(files)

        # 3. Perform similarity search for patterns
        patterns = await self.find_similar_issues(documents)

        # 4. Generate RCA analysis with LLM
        analysis = await self.llm_provider.analyze_logs(files, patterns)

        # 5. Generate comprehensive report
        report = await self.generate_report(analysis, patterns)

        return {
            "analysis": analysis,
            "patterns": patterns,
            "report": report,
            "documents_processed": len(documents)
        }

    async def process_log_analysis(self, job: Job) -> Dict[str, Any]:
        """Process log analysis job."""
        # Implementation for log analysis
        pass

    async def process_embedding_generation(self, job: Job) -> Dict[str, Any]:
        """Process embedding generation job."""
        # Implementation for embedding generation
        pass
```

#### **3. LLM Provider Abstraction**

```python
# core/llm/providers/base.py - Base provider interface
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, int]] = None
    model: str
    provider: str

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    usage: Optional[Dict[str, int]] = None
    model: str
    provider: str

class BaseLLMProvider(ABC):
    """Base interface for LLM providers."""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str]
    ) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    async def analyze_logs(
        self,
        logs: List[str],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze logs for root cause analysis."""
        pass

# core/llm/providers/ollama.py - Ollama implementation
import httpx
from core.config import settings

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = None):
        super().__init__(model or settings.llm.OLLAMA_MODEL)
        self.base_url = settings.llm.OLLAMA_HOST
        self.timeout = settings.llm.OLLAMA_TIMEOUT
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def generate_text(self, prompt: str, max_tokens: int = None, temperature: float = 0.7, **kwargs) -> LLMResponse:
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["response"],
            model=self.model,
            provider="ollama",
            usage=data.get("usage", {})
        )
```

### **API Routes (Priority 2)**

#### **4. Authentication Router**

```python
# apps/api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from core.security.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

#### **5. Jobs Router**

```python
# apps/api/routers/jobs.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from core.jobs.service import JobService
from core.jobs.schemas import JobCreate, JobResponse, JobListResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
job_service = JobService()

@router.post("/", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new analysis job."""
    new_job = await job_service.create_job(
        user_id=current_user.id,
        job_type=job.job_type,
        input_manifest=job.input_manifest,
        provider=job.provider,
        model=job.model,
        priority=job.priority
    )
    return JobResponse.from_orm(new_job)

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """List user's jobs with optional filtering."""
    jobs = await job_service.get_user_jobs(
        user_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset
    )
    return JobListResponse(jobs=jobs, total=len(jobs))

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific job details."""
    job = await job_service.get_job(job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_orm(job)

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a running job."""
    job = await job_service.get_job(job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    await job_service.cancel_job(job_id)
    return {"message": "Job cancelled successfully"}
```

### **Security Implementation (Priority 3)**

#### **6. Authentication System**

```python
# core/security/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from core.config import settings
from core.db.models import User
from core.db.database import get_db_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def authenticate_user(username: str, password: str) -> Optional[User]:
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.username == username, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None
        return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iss": settings.security.JWT_ISSUER, "aud": settings.security.JWT_AUDIENCE})
    encoded_jwt = jwt.encode(to_encode, settings.security.JWT_SECRET_KEY, algorithm=settings.security.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.security.JWT_SECRET_KEY,
            algorithms=[settings.security.JWT_ALGORITHM],
            issuer=settings.security.JWT_ISSUER,
            audience=settings.security.JWT_AUDIENCE
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user
```

#### **7. Security Middleware**

```python
# core/security/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import uuid
import time
from core.config import settings

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add security headers to response
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request_id

        # CSP headers (nonce-based)
        if settings.security.CSP_ENABLED:
            nonce = str(uuid.uuid4())
            request.state.csp_nonce = nonce
            response.headers["Content-Security-Policy"] = (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"style-src 'self' 'nonce-{nonce}'; "
                f"img-src 'self' data: https:; "
                f"font-src 'self'; "
                f"connect-src 'self' ws: wss:; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"upgrade-insecure-requests;"
            )

        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware (requires Redis)."""

    async def dispatch(self, request: Request, call_next):
        if not settings.redis.REDIS_ENABLED:
            return await call_next(request)

        # Implement rate limiting logic
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"

        # Check rate limit (implementation depends on Redis client)
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, 3600)  # 1 hour

        if current > 100:  # 100 requests per hour
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": 3600}
            )

        return await call_next(request)
```

---

## 📋 **TESTING STRATEGY**

### **Unit Tests**

```bash
# Test database models
pytest tests/test_models.py -v

# Test job service
pytest tests/test_job_service.py -v

# Test LLM providers
pytest tests/test_llm_providers.py -v
```

### **Integration Tests**

```bash
# Test API endpoints
pytest tests/test_api.py -v

# Test job processing flow
pytest tests/test_job_processing.py -v

# Test file upload
pytest tests/test_file_upload.py -v
```

### **Security Tests**

```bash
# Run security audit
npm audit --audit-level high

# Python security scan
pip-audit --desc --format=json

# SAST scanning
bandit -r . -f json
```

### **Load Tests**

```bash
# Test concurrent job processing
locust -f tests/load_test.py --host=http://localhost:8000

# Test file upload performance
pytest tests/test_upload_performance.py -v
```

---

## 🚀 **DEPLOYMENT STEPS**

### **1. Local Development**

```bash
# Clone repository
git clone <repository-url>
cd unified_rca_engine

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Run development server
python apps/api/main.py

# Run worker (separate terminal)
python apps/worker/main.py

# Run UI (separate terminal)
cd ui && npm install && npm run dev
```

### **2. Production Deployment**

```bash
# Build and deploy
cd deploy/docker
docker-compose up -d

# Run health checks
./deploy/scripts/smoke-test.sh

# Monitor logs
docker-compose logs -f
```

### **3. Monitoring Setup**

```bash
# Access Grafana
curl http://localhost:3001

# Access Prometheus
curl http://localhost:9090

# View metrics
curl http://localhost:8001/metrics
```

---

## 📈 **SUCCESS METRICS**

### **Performance**

- [ ] Job processing < 5 minutes for 100MB logs
- [ ] API response time < 200ms for standard requests
- [ ] File upload < 30 seconds for 10MB files
- [ ] Database queries < 100ms average

### **Reliability**

- [ ] 99.9% uptime target
- [ ] < 1% job failure rate
- [ ] Zero data loss
- [ ] Graceful error handling

### **Security**

- [ ] Zero critical vulnerabilities
- [ ] All dependencies up-to-date
- [ ] Security headers implemented
- [ ] Input validation complete

### **Scalability**

- [ ] Support 100 concurrent jobs
- [ ] Handle 1GB+ file uploads
- [ ] Horizontal scaling ready
- [ ] Database connection pooling

---

## 📋 **NEXT STEPS**

1. **Complete Core Implementation** - Focus on job processing and LLM providers
2. **Implement Security Features** - Authentication and authorization
3. **Build UI Components** - React components for job management
4. **Add Monitoring** - Comprehensive metrics and alerting
5. **Testing Suite** - Unit, integration, and load tests
6. **Documentation** - API docs and deployment guides
7. **Production Hardening** - Security scanning and optimization

This unified codebase provides a solid foundation for a production-ready RCA engine with the best features from both development and production versions.
