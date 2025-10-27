# Performance Optimizations - Quick Reference

Quick guide for using the newly implemented performance optimizations.

## 🚀 New Endpoints

### Health & Monitoring
```bash
# Simple health check (cached for 30s)
curl http://localhost:8000/health/live

# Database + dependencies check
curl http://localhost:8000/health/deep

# Connection pool statistics (cached for 10s)
curl http://localhost:8000/health/pool

# Cache statistics
curl http://localhost:8000/health/cache
```

## 💻 Code Examples

### 1. Use Response Caching
```python
from core.cache.response_cache import cached

# Cache endpoint responses
@router.get("/expensive-operation")
@cached(ttl=60)  # Cache for 60 seconds
async def expensive_operation():
    # Expensive computation here
    return {"result": "data"}

# Cache with custom key prefix
@cached(ttl=300, key_prefix="stats")
async def get_statistics(user_id: int):
    # Results cached per user_id
    return compute_stats(user_id)

# Check cache statistics
from core.cache.response_cache import cache
stats = cache.get_statistics()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

### 2. Use Optimized Job Queries
```python
from core.jobs.service import JobService

service = JobService()

# Automatically uses deferred loading for large fields
job = await service.get_job(job_id)  # Only loads metadata

# Access deferred fields when needed (lazy load)
full_result = job.raw_result  # Loaded on demand
```

### 3. Batch Embedding Generation
```python
from core.llm.embeddings import EmbeddingService

service = EmbeddingService()
await service.initialize()

# Old way (one-by-one, slow)
embeddings = []
for text in texts:
    embedding = await service.embed_text(text)
    embeddings.append(embedding)

# New way (batched, fast)
embeddings = await service.embed_documents(texts, batch_size=50)
```

### 4. Job Checkpoints (Resume on Failure)
```python
from core.jobs.checkpoint import get_checkpoint_manager

checkpoint = get_checkpoint_manager().get_checkpoint(job_id)

# Save progress after each stage
await checkpoint.save('redaction', {'files_processed': 5})
await checkpoint.save('embedding', {'chunks_embedded': 42})

# Resume on restart
data = await checkpoint.load()
if data:
    stage = data['stage']  # 'embedding'
    # Skip completed stages, resume from here
```

### 5. Streaming File Uploads
```python
from pathlib import Path
from core.files.streaming import process_multipart_upload

# Handles large files efficiently
metadata = await process_multipart_upload(
    file=uploaded_file,
    destination_dir=Path("/uploads"),
    max_file_size=500 * 1024 * 1024  # 500MB limit
)

print(f"Uploaded: {metadata['filename']}")
print(f"Hash: {metadata['hash']}")
print(f"Size: {metadata['size']} bytes")
```

### 6. Enhanced Structured Logging
```python
from core.logging import get_logger

logger = get_logger(__name__)

# Automatically includes context
logger.info(
    "Job processing completed",
    extra={
        'job_id': job.id,
        'user_id': user.id,
        'duration_ms': 1234.5,
        'files_processed': 10
    }
)

# Output (JSON format):
# {
#   "timestamp": "2025-10-22T23:00:00Z",
#   "level": "INFO",
#   "message": "Job processing completed",
#   "context": {
#     "job_id": "abc-123",
#     "user_id": "user-456",
#     "duration_ms": 1234.5,
#     "files_processed": 10
#   }
# }
```

## 🔧 Configuration

### Enable Request Deduplication
Add to `apps/api/main.py`:
```python
from apps.api.middleware import RequestDeduplicationMiddleware

app.add_middleware(
    RequestDeduplicationMiddleware,
    window_seconds=5,        # Duplicate window
    max_cache_size=1000      # Max requests to track
)
```

### Adjust Embedding Batch Size
```python
# Smaller batches for rate-limited APIs
embeddings = await service.embed_documents(texts, batch_size=10)

# Larger batches for local models
embeddings = await service.embed_documents(texts, batch_size=100)
```

### Configure Checkpoint Cleanup
```python
from core.jobs.checkpoint import get_checkpoint_manager

manager = get_checkpoint_manager()

# Clean up checkpoints older than 24 hours
cleaned = await manager.cleanup_old_checkpoints(max_age_hours=24)
print(f"Cleaned {cleaned} old checkpoints")
```

## 📊 Monitoring Commands

### Check Connection Pool Health
```python
from core.db.database import db_manager

stats = db_manager.get_pool_stats()
print(f"Pool size: {stats['pool_size']}")
print(f"In use: {stats['checked_out']}")
print(f"Available: {stats['checked_in']}")
print(f"Overflow: {stats['overflow']}")
```

### List Active Checkpoints
```python
from core.jobs.checkpoint import get_checkpoint_manager

checkpoints = await get_checkpoint_manager().list_checkpoints()
for cp in checkpoints:
    print(f"Job {cp['job_id']}: stage={cp['stage']}, time={cp['timestamp']}")
```

## 🗃️ Database Migrations

### Apply Performance Indexes
```bash
# Apply the new indexes
alembic upgrade head

# Verify indexes were created
psql -h localhost -p 15433 -U rca_user -d rca_engine -c "\d+ jobs"
```

### Rollback Indexes (if needed)
```bash
alembic downgrade -1
```

## 🧪 Testing

### Test LLM Fallback
```python
from core.llm.manager import LLMProviderManager
from core.llm.providers import LLMMessage

manager = LLMProviderManager(
    primary_provider="openai",
    max_retries=3
)

messages = [LLMMessage(role="user", content="Hello!")]

# Will automatically fallback if OpenAI fails
response = await manager.generate(messages)
```

### Test Request Deduplication
```bash
# Send first request
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "test"}'

# Send duplicate immediately (should get 429)
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "test"}'

# Response: {"error": "Duplicate request detected"}
```

## ⚠️ Important Notes

1. **Deferred Loading**: Accessing deferred fields (`job.raw_result`) will trigger a database query
2. **Checkpoints**: Stored in `/tmp/rca_checkpoints` by default (configure for production)
3. **Indexes**: Created with `CONCURRENTLY` to avoid locking tables
4. **Deduplication**: Only applies to POST/PUT/PATCH methods
5. **Batch Size**: Tune based on your LLM provider's rate limits

## 🎯 Common Use Cases

### Scenario 1: Job Fails During Embedding
```python
# Job processor code
checkpoint = get_checkpoint_manager().get_checkpoint(job.id)

# Check for existing checkpoint
existing = await checkpoint.load()
if existing and existing['stage'] == 'redaction':
    # Skip redaction, go straight to embedding
    start_stage = 'embedding'
else:
    start_stage = 'redaction'

# Process with checkpoints
if start_stage <= 'redaction':
    await redact_pii(job)
    await checkpoint.save('redaction')

if start_stage <= 'embedding':
    await generate_embeddings(job)
    await checkpoint.save('embedding')
```

### Scenario 2: Monitor High Database Load
```bash
# Check pool continuously
watch -n 1 'curl -s http://localhost:8000/health/pool | jq'

# Look for:
# - checked_out approaching pool_size (need more connections)
# - overflow > 0 (using overflow connections)
```

### Scenario 3: Process Large File Upload
```python
@router.post("/upload")
async def upload_large_file(file: UploadFile):
    from core.files.streaming import StreamingFileProcessor
    
    processor = StreamingFileProcessor(
        chunk_size=1024 * 1024,  # 1MB chunks
        max_file_size=1024 * 1024 * 1024  # 1GB limit
    )
    
    destination = Path(f"/uploads/{file.filename}")
    hash, size = await processor.process_upload(file, destination)
    
    return {
        "filename": file.filename,
        "hash": hash,
        "size": size
    }
```

## 📚 Further Reading

- See `PERFORMANCE_OPTIMIZATIONS_COMPLETE.md` for detailed documentation
- Check individual module docstrings for API details
- Review test files for usage examples

---

**Questions?** Check the main documentation or reach out to the team!
