# Archive Issues Troubleshooting Guide

## Quick Diagnosis

Use this flowchart to diagnose common archive extraction issues:

```
Archive Extraction Failing?
├─ "Unsupported archive type"
│  └─ See: Unsupported Format Error
├─ "Exceeded size limit"
│  └─ See: Size Limit Exceeded
├─ "Extraction timeout"
│  └─ See: Extraction Timeout
├─ "Excessive decompression ratio"
│  └─ See: Decompression Ratio Violation
├─ "Too many members"
│  └─ See: Member Count Violation
└─ "Path traversal detected"
   └─ See: Path Traversal Detected
```

## Common Issues

### Unsupported Format Error

**Symptoms**:
```
ERROR: Unsupported archive type: .rar
```

**Cause**: Archive format is not supported by the platform.

**Supported Formats**:
- `.zip` - ZIP archives
- `.gz` - Gzip (single file or `.tar.gz`)
- `.bz2` - Bzip2 (single file or `.tar.bz2`)
- `.xz` - XZ/LZMA (single file or `.tar.xz`)
- `.tar` - Uncompressed tar
- `.tgz`, `.tbz2`, `.txz` - Shorthand tar formats

**Solutions**:

1. **Convert to Supported Format**:
   ```bash
   # Convert RAR to ZIP
   unrar x archive.rar temp/
   cd temp && zip -r ../archive.zip .
   
   # Convert 7z to TAR.GZ
   7z x archive.7z -otemp/
   cd temp && tar czf ../archive.tar.gz .
   ```

2. **Extract Locally First**:
   Extract the archive on your machine, then create a supported archive:
   ```bash
   # Linux/Mac
   tar czf output.tar.gz /path/to/extracted/files
   
   # Windows (PowerShell)
   Compress-Archive -Path "C:\extracted\*" -DestinationPath output.zip
   ```

3. **Contact Support**:
   If you frequently need unsupported formats, request support for additional formats.

---

### Size Limit Exceeded

**Symptoms**:
```
ERROR: Archive extraction exceeded size limit of 104857600 bytes
```

**Cause**: Extracted content exceeds the configured size limit (default: 100 MB).

**Diagnosis**:
```python
# Check extracted size before upload
import tarfile
total = sum(m.size for m in tarfile.open('archive.tar.gz').getmembers())
print(f"Uncompressed size: {total / 1024 / 1024:.2f} MB")
```

**Solutions**:

1. **Split Archive into Smaller Parts**:
   ```bash
   # Split tar.gz into 50MB chunks
   tar czf - large_directory/ | split -b 50M - archive_part_
   
   # Recombine on destination
   cat archive_part_* | tar xz
   ```

2. **Filter Unnecessary Files**:
   ```bash
   # Exclude large binary files
   tar czf logs.tar.gz --exclude='*.bin' --exclude='*.exe' logs/
   
   # Include only specific file types
   find logs/ -name "*.log" -o -name "*.txt" | tar czf logs.tar.gz -T -
   ```

3. **Request Limit Increase**:
   Contact your administrator to increase the size limit:
   ```python
   extractor = ArchiveExtractor(size_limit_bytes=500 * 1024 * 1024)  # 500 MB
   ```

---

### Extraction Timeout

**Symptoms**:
```
ERROR: Archive extraction exceeded timeout of 30 seconds
```

**Cause**: Extraction took longer than the configured timeout.

**Common Causes**:
- Very large archives
- Slow disk I/O
- High system load
- Excessive file count

**Solutions**:

1. **Use More Efficient Compression**:
   ```bash
   # XZ is slow to decompress - use gzip instead
   tar czf fast.tar.gz files/    # Gzip (fast)
   # Instead of:
   tar cJf slow.tar.xz files/    # XZ (slow)
   ```

2. **Reduce Archive Size**:
   - Split into smaller archives
   - Remove unnecessary files
   - Use appropriate compression level

3. **Increase Timeout** (Administrator):
   ```python
   extractor = ArchiveExtractor(timeout_seconds=60)  # 60 seconds
   ```

---

### Decompression Ratio Violation

**Symptoms**:
```
WARNING: Decompression ratio too high (450.0:1)
ERROR: Excessive decompression ratio detected
```

**Cause**: Archive has an unusually high compression ratio, indicating a potential decompression bomb (zip bomb).

**Safeguard Threshold**: 100:1 (uncompressed:compressed)

**Diagnosis**:
```bash
# Check ratio before upload
compressed=$(stat -f%z archive.tar.gz)
uncompressed=$(tar tzf archive.tar.gz | xargs stat -f%z | awk '{s+=$1} END {print s}')
ratio=$((uncompressed / compressed))
echo "Ratio: ${ratio}:1"
```

**Solutions**:

1. **Verify Archive is Not Malicious**:
   - Scan with antivirus
   - Verify source is trusted
   - Inspect archive contents locally

2. **Re-compress with Normal Ratio**:
   ```bash
   # Extract and recompress with less aggressive settings
   tar xzf suspicious.tar.gz
   tar czf --fast normalized.tar.gz extracted/  # Use --fast for lower compression
   ```

3. **Split Highly Compressible Content**:
   If content is legitimately highly compressible (e.g., text logs with repeated patterns):
   ```bash
   # Split into smaller archives
   split -l 10000 large.log split_
   for f in split_*; do gzip "$f"; done
   ```

4. **Request Ratio Increase** (with justification):
   ```python
   config = SafeguardConfig(max_decompression_ratio=200.0)
   ```

---

### Member Count Violation

**Symptoms**:
```
ERROR: Archive contains too many members (15000)
ERROR: Excessive member count detected
```

**Cause**: Archive contains more than 10,000 files.

**Safeguard Threshold**: 10,000 files per archive

**Diagnosis**:
```bash
# Count files in archive
zipinfo -1 archive.zip | wc -l        # ZIP
tar tzf archive.tar.gz | wc -l        # TAR.GZ
```

**Solutions**:

1. **Consolidate Small Files**:
   ```bash
   # Merge small log files
   find logs/ -name "*.log" -exec cat {} + > combined.log
   gzip combined.log
   ```

2. **Create Multiple Archives**:
   ```bash
   # Split by directory
   tar czf logs_part1.tar.gz logs/2024-01/
   tar czf logs_part2.tar.gz logs/2024-02/
   
   # Split by file count
   find logs/ -type f | split -l 5000 - file_list_
   for list in file_list_*; do
       tar czf "archive_$(basename $list).tar.gz" -T "$list"
   done
   ```

3. **Request Limit Increase**:
   ```python
   config = SafeguardConfig(max_member_count=50000)
   ```

---

### Path Traversal Detected

**Symptoms**:
```
ERROR: Archive member attempts path traversal: ../../../etc/passwd
ERROR: Path traversal attempt detected
```

**Cause**: Archive contains files with paths designed to escape the extraction directory.

**Detection Patterns**:
- Absolute paths: `/etc/passwd`
- Parent references: `../../sensitive/file`

**Solutions**:

1. **Remove Malicious Paths**:
   ```bash
   # Extract safely, removing path components
   tar xzf suspicious.tar.gz --strip-components=3
   
   # Or use --transform to sanitize paths
   tar xzf archive.tar.gz --transform='s|^.*/||'
   ```

2. **Recreate Archive Without Traversal**:
   ```bash
   # Extract to temp, then repackage
   mkdir safe_extract
   cd safe_extract
   tar xzf ../suspicious.tar.gz
   # Remove any files in unexpected locations
   tar czf ../safe_archive.tar.gz .
   ```

3. **Report Suspicious Archives**:
   Archives with path traversal attempts may be malicious. Report to security team.

---

## Advanced Troubleshooting

### Inspecting Archive Contents

**Without Extraction**:
```bash
# List ZIP contents
unzip -l archive.zip

# List TAR.GZ contents with sizes
tar tzvf archive.tar.gz

# Show first 20 files
tar tzf archive.tar.gz | head -20

# Search for specific files
tar tzf archive.tar.gz | grep "error"
```

### Testing Archive Integrity

```bash
# Test ZIP integrity
unzip -t archive.zip

# Test TAR.GZ integrity
tar tzf archive.tar.gz > /dev/null

# Test GZIP integrity
gzip -t file.gz

# Test BZIP2 integrity
bzip2 -t file.bz2
```

### Extracting Specific Files

```bash
# Extract single file from ZIP
unzip archive.zip specific/file.log

# Extract single file from TAR.GZ
tar xzf archive.tar.gz specific/file.log

# Extract files matching pattern
tar xzf archive.tar.gz --wildcards "*.log"
```

### Performance Analysis

```bash
# Time extraction
time tar xzf archive.tar.gz

# Monitor disk usage during extraction
df -h . & tar xzf archive.tar.gz

# Check extraction speed
pv archive.tar.gz | tar xz
```

## Database Diagnostics

### Query Extraction Audit Trail

```sql
-- Recent extractions with violations
SELECT 
    source_filename,
    archive_type,
    member_count,
    decompression_ratio,
    guardrail_status,
    blocked_reason
FROM archive_extraction_audits
WHERE guardrail_status != 'passed'
ORDER BY completed_at DESC
LIMIT 20;

-- Archives with high ratios
SELECT 
    source_filename,
    decompression_ratio,
    compressed_size_bytes / 1024 / 1024 as compressed_mb,
    estimated_uncompressed_bytes / 1024 / 1024 as uncompressed_mb
FROM archive_extraction_audits
WHERE decompression_ratio > 50
ORDER BY decompression_ratio DESC;

-- Extraction timeouts
SELECT 
    job_id,
    source_filename,
    archive_type,
    blocked_reason
FROM archive_extraction_audits
WHERE guardrail_status = 'timeout';
```

## Prevention Strategies

### For Users

1. **Test Archives Locally**:
   ```bash
   # Verify archive before upload
   tar tzf archive.tar.gz > /dev/null && echo "OK" || echo "CORRUPT"
   ```

2. **Use Appropriate Compression**:
   - Text logs: gzip (fast, good ratio)
   - Binary data: xz (slow, best ratio)
   - Mixed: zip (universal compatibility)

3. **Organize Before Archiving**:
   ```bash
   # Good structure
   logs/
   ├── application/
   │   ├── app.log
   │   └── error.log
   └── system/
       └── syslog
   
   # Not recommended
   thousands_of_loose_files/
   ```

### For Administrators

1. **Configure Appropriate Limits**:
   ```python
   # For high-volume environments
   SafeguardConfig(
       max_decompression_ratio=150.0,
       max_member_count=20000,
   )
   ```

2. **Monitor Trends**:
   - Track average archive sizes
   - Identify users with frequent violations
   - Adjust thresholds based on patterns

3. **Automate Validation**:
   ```bash
   # Pre-upload validation script
   ./scripts/pipeline/ingest_archive.py "$archive" --strict
   ```

## Getting Help

### Information to Collect

When reporting archive extraction issues, include:

1. **Archive Details**:
   - Filename and format
   - Compressed size
   - Number of files
   - Creation tool/version

2. **Error Messages**:
   - Complete error output
   - Relevant log excerpts
   - Audit record ID

3. **Environment**:
   - Platform version
   - Operating system
   - Disk space available
   - System load

### Support Channels

- **Documentation**: [Archive Handling Guide](../operations/archive-handling.md)
- **CLI Tool**: `python scripts/pipeline/ingest_archive.py --help`
- **API Reference**: `/api/v1/docs#/files`

## Related Documentation

- [Archive Handling Operations Guide](../operations/archive-handling.md)
- [File Upload Guide](../getting-started/file-upload.md)
- [Security Best Practices](../reference/security.md)
