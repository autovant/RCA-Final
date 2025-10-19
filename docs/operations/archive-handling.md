# Archive Handling Operations Guide

## Overview

The RCA platform supports extraction of multiple archive formats with built-in safeguards to prevent decompression bombs and other security threats. This guide covers supported formats, safeguard mechanisms, and operational procedures.

## Supported Archive Formats

### Single-File Compression

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **Gzip** | `.gz` | GNU zip compression | Individual log files |
| **Bzip2** | `.bz2` | Bzip2 compression | Better compression than gzip |
| **XZ/LZMA** | `.xz` | LZMA compression | Highest compression ratio |

### Multi-File Archives

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **ZIP** | `.zip` | ZIP archive | Cross-platform archive bundles |
| **TAR** | `.tar` | Uncompressed tar | Unix file collections |
| **TAR+Gzip** | `.tar.gz`, `.tgz` | Gzip compressed tar | Most common Unix archive |
| **TAR+Bzip2** | `.tar.bz2`, `.tbz2` | Bzip2 compressed tar | Better compression |
| **TAR+XZ** | `.tar.xz`, `.txz` | XZ compressed tar | Best compression |

## Safeguard Mechanisms

### Decompression Ratio Check

**Purpose**: Prevent decompression bombs (zip bombs) where small compressed files expand to enormous sizes.

**Threshold**: Maximum ratio of 100:1 (uncompressed:compressed size)

**Example**:
- Compressed: 1 MB
- Uncompressed: ≤100 MB ✓ Pass
- Uncompressed: 500 MB ✗ Blocked

**Configuration**:
```python
from core.files.validators import SafeguardConfig

config = SafeguardConfig(
    max_decompression_ratio=100.0  # Adjust as needed
)
```

### Member Count Limit

**Purpose**: Prevent excessive file count that can exhaust system resources.

**Threshold**: Maximum 10,000 files per archive

**Example**:
- 5,000 files ✓ Pass
- 15,000 files ✗ Blocked

**Configuration**:
```python
config = SafeguardConfig(
    max_member_count=10000  # Adjust as needed
)
```

### Path Traversal Prevention

**Purpose**: Block archives containing files that attempt to escape extraction directory.

**Detection**:
- Absolute paths (starting with `/`)
- Parent directory references (`../`)

**Example**:
- `logs/file.txt` ✓ Safe
- `../../../etc/passwd` ✗ Blocked
- `/etc/shadow` ✗ Blocked

### Size and Timeout Limits

**Purpose**: Prevent resource exhaustion during extraction.

**Thresholds**:
- Maximum extraction size: 100 MB (default)
- Maximum extraction time: 30 seconds (default)

**Configuration**:
```python
from core.files.extraction import ArchiveExtractor

extractor = ArchiveExtractor(
    size_limit_bytes=100 * 1024 * 1024,  # 100 MB
    timeout_seconds=30
)
```

## Operational Procedures

### Manual Archive Inspection

Use the CLI tool to validate archives before ingestion:

```bash
# Basic inspection
python scripts/pipeline/ingest_archive.py logs.tar.gz

# Strict mode (block on any warnings)
python scripts/pipeline/ingest_archive.py suspicious.zip --strict

# Custom safeguard limits
python scripts/pipeline/ingest_archive.py large.tar.bz2 \
    --max-ratio 200 \
    --max-members 50000
```

### Programmatic Extraction

```python
from pathlib import Path
from core.files.extraction import ArchiveExtractor
from core.files.validation import validate_archive_before_extraction

archive_path = Path("uploads/data.tar.gz")

# Pre-extraction safeguard check
violations = validate_archive_before_extraction(archive_path)
if violations:
    print("Safeguard violations detected:")
    for v in violations:
        print(f"  - {v.code}: {v.message}")
    # Decide whether to proceed

# Extract with safeguards
extractor = ArchiveExtractor()
result = extractor.extract(archive_path)

print(f"Extracted {len(result.files)} files")
print(f"Total size: {result.total_size_bytes / 1024 / 1024:.2f} MB")
print(f"Duration: {result.duration_seconds:.2f}s")

# Cleanup when done
result.cleanup()
```

### Audit Trail

All extractions are logged in the `ArchiveExtractionAudit` table:

```python
from core.files.audit import get_extraction_audit

# Retrieve audit record
audit = await get_extraction_audit(session, job_id)

if audit:
    print(f"Archive: {audit.source_filename}")
    print(f"Type: {audit.archive_type}")
    print(f"Members: {audit.member_count}")
    print(f"Ratio: {audit.decompression_ratio}:1")
    print(f"Status: {audit.guardrail_status}")
    if audit.blocked_reason:
        print(f"Blocked: {audit.blocked_reason}")
```

## Monitoring and Alerting

### Key Metrics

Monitor these metrics for archive processing health:

1. **Guardrail Block Rate**:
   ```sql
   SELECT 
       guardrail_status,
       COUNT(*) 
   FROM archive_extraction_audits 
   GROUP BY guardrail_status;
   ```

2. **Average Decompression Ratio**:
   ```sql
   SELECT 
       archive_type,
       AVG(decompression_ratio) as avg_ratio
   FROM archive_extraction_audits
   WHERE decompression_ratio IS NOT NULL
   GROUP BY archive_type;
   ```

3. **Extraction Failures**:
   ```sql
   SELECT 
       COUNT(*) 
   FROM archive_extraction_audits 
   WHERE guardrail_status IN ('error', 'timeout');
   ```

### Alert Thresholds

Configure alerts for:

- **High Block Rate**: > 10% of extractions blocked
- **Excessive Ratios**: Average ratio > 50:1 for a job
- **Timeouts**: > 5% of extractions timing out
- **Large Archives**: Archives > 500 MB compressed

## Best Practices

### For Users

1. **Pre-compress Logs**: Use appropriate compression for log types
   - Text logs: `.tar.gz` or `.tar.bz2`
   - Binary logs: `.tar.xz` for best compression
   - Mixed content: `.zip` for compatibility

2. **Split Large Archives**: Break archives > 100 MB into smaller chunks

3. **Organize Files**: Use directory structure within archives for clarity

4. **Test Locally**: Verify archives extract correctly before upload

### For Operators

1. **Monitor Audit Logs**: Review blocked extractions regularly

2. **Adjust Thresholds**: Tune safeguards based on workload patterns

3. **Resource Planning**: Allocate sufficient disk space for extraction temp directories

4. **Incident Response**: Investigate repeated blocks from same source

## Security Considerations

### Threat Model

The safeguards protect against:

1. **Zip Bombs**: Small archives that expand to massive sizes
2. **Path Traversal**: Files escaping extraction directory
3. **Resource Exhaustion**: Excessive files or extraction time
4. **Malicious Archives**: Crafted to exploit decompression vulnerabilities

### Limitations

Safeguards cannot prevent:

- Malicious file content (use anti-malware scanning)
- Encrypted archives (cannot inspect contents)
- Social engineering attacks

### Defense in Depth

Combine archive safeguards with:

- File content validation
- Malware scanning
- User authentication and authorization
- Rate limiting on uploads
- Storage quotas

## Configuration Reference

### Environment Variables

```bash
# Extraction limits
export RCA_ARCHIVE_MAX_SIZE_MB=100
export RCA_ARCHIVE_MAX_TIMEOUT_SEC=30

# Safeguard thresholds
export RCA_ARCHIVE_MAX_RATIO=100
export RCA_ARCHIVE_MAX_MEMBERS=10000
```

### Database Configuration

Audit retention policy:

```sql
-- Delete old audit records (older than 90 days)
DELETE FROM archive_extraction_audits
WHERE completed_at < NOW() - INTERVAL '90 days';
```

## Troubleshooting

For detailed troubleshooting guidance, see:
- [Archive Issues Troubleshooting Guide](../troubleshooting/archive-issues.md)
- [File Upload Issues](../troubleshooting/file-upload.md)

## Related Documentation

- [File Upload Guide](../getting-started/file-upload.md)
- [Job Processing Pipeline](../reference/job-processing.md)
- [Security Best Practices](../reference/security.md)
