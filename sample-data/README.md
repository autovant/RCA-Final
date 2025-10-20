# Sample Data Directory

This directory contains sample log files used for demos, testing, and showcasing RCA Engine capabilities.

## Demo Files (for Feature Showcase)

### 1. demo-app-with-pii.log
**Purpose:** Demonstrates PII detection and redaction capabilities

**Contents:**
- 27 lines of realistic application logs
- 8+ types of PII data:
  - Email addresses (3)
  - Social Security Numbers (1)
  - Phone numbers (1)
  - Physical addresses (1)
  - Credit card numbers (1)
  - API keys (1)
  - Session tokens (1)
- Database connection errors
- Service degradation scenario

**Use Cases:**
- Demo PII redaction before AI processing
- Show GDPR/CCPA compliance
- Demonstrate classification of error levels
- Showcase privacy protection features

**Demo Route:** `/demo/showcase` → "Application Logs with PII"

---

### 2. demo-blueprism-error.log
**Purpose:** Demonstrates Blue Prism platform detection and RPA analysis

**Contents:**
- 38 lines of Blue Prism specific logs
- Platform identifiers:
  - "Blue Prism Server v7.2.1"
  - Runtime Resources
  - Work queues
  - Process/Object/Stage terminology
  - Business exceptions
- SAP GUI connection failure scenario
- Automatic retry attempts
- Exception rate threshold alerts

**Use Cases:**
- Demo platform auto-detection
- Show RPA-specific analysis
- Demonstrate connector issue diagnosis
- Showcase retry mechanism analysis

**Demo Route:** `/demo/showcase` → "Blue Prism RPA Failure"

---

### 3. demo-uipath-selector-error.log
**Purpose:** Demonstrates UiPath platform detection and UI automation analysis

**Contents:**
- 33 lines of UiPath specific logs
- Platform identifiers:
  - "UiPath.Executor.Main"
  - "UiPath.Activities"
  - Orchestrator integration
  - Selector syntax
  - Screenshot capture
- UI element selector timeout scenario
- Retry mechanism (3 attempts)
- SelectorNotFoundException
- Transaction statistics

**Use Cases:**
- Demo platform auto-detection for UiPath
- Show UI automation failure analysis
- Demonstrate selector issue diagnosis
- Showcase screenshot detection

**Demo Route:** `/demo/showcase` → "UiPath Selector Error"

---

## Using Demo Files

### In Web UI
Navigate to `/demo/showcase` and select a demo scenario. The files will be automatically served through the internal API.

### Manual Upload
You can also manually upload these files through the standard investigation workflow:
1. Go to `/investigation`
2. Click "Upload Files"
3. Select one or more demo files
4. Configure job settings
5. Submit for analysis

### API Testing
```bash
# Upload file via API
curl -X POST http://localhost:8001/api/files/upload \
  -F "file=@sample-data/demo-app-with-pii.log"

# Create analysis job
curl -X POST http://localhost:8001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "rca_analysis",
    "provider": "copilot",
    "model": "gpt-4",
    "file_ids": ["<file_id>"]
  }'
```

---

## Creating New Demo Files

When creating new demo files for the showcase:

1. **Name Convention:** `demo-<platform>-<scenario>.log`
   - Example: `demo-automation-anywhere-crash.log`

2. **Content Requirements:**
   - Realistic log format matching the platform
   - Clear scenario (error, failure, timeout, etc.)
   - 20-50 lines (enough context, not overwhelming)
   - Include platform-specific identifiers

3. **For PII Demos:**
   - Include diverse PII types
   - Use fake but realistic data
   - Format: `john.doe@acmecorp.com` (not `user@example.com`)
   - Avoid real personal information

4. **For Platform Detection:**
   - Include version strings
   - Use platform-specific terminology
   - Add unique identifiers (e.g., "UiPath.Executor")

5. **Add to Showcase:**
   - Update `ui/src/app/api/demo-files/[filename]/route.ts` whitelist
   - Add entry to `DEMO_FILES` in `ui/src/app/demo/showcase/page.tsx`
   - Update detection logic if new platform

---

## Security Notes

**Demo File Access:**
- Demo files are served through a controlled API endpoint
- Only whitelisted files can be accessed
- No directory traversal attacks possible
- Files are read-only

**PII in Demo Files:**
- All PII data is FAKE
- No real personal information is used
- Data is intentionally included for demonstration purposes
- Should never contain actual sensitive data

---

## Directory Structure

```
sample-data/
├── README.md                          # This file
├── demo-app-with-pii.log             # PII redaction demo
├── demo-blueprism-error.log          # Blue Prism platform demo
├── demo-uipath-selector-error.log    # UiPath platform demo
└── [other test/sample files...]
```

---

## Related Documentation

- **Feature Showcase Guide:** `docs/DEMO_SHOWCASE_COMPLETE.md`
- **PII Protection Guide:** `docs/PII_PROTECTION_GUIDE.md`
- **Platform Detection:** (see `core/llm/detection.py`)

---

## Testing with Demo Files

### Unit Tests
```python
# Test PII detection
def test_pii_detection_with_demo_file():
    with open("sample-data/demo-app-with-pii.log") as f:
        content = f.read()
        detector = PIIDetector()
        results = detector.scan(content)
        assert len(results) >= 8  # Should find at least 8 PII items
```

### Integration Tests
```python
# Test platform detection
def test_platform_detection_with_demo_file():
    with open("sample-data/demo-blueprism-error.log") as f:
        content = f.read()
        detector = PlatformDetector()
        platform = detector.detect(content)
        assert platform == "Blue Prism"
        assert "7.2.1" in platform.version
```

---

## Maintenance

**When to Update:**
- New RPA platforms are supported
- New PII types are detected
- Demo scenarios become outdated
- Client feedback suggests new use cases

**Review Schedule:**
- Quarterly: Check if demo files reflect current capabilities
- After major releases: Update version strings and features
- When adding features: Create demo file showcasing new capability

---

**Last Updated:** January 12, 2025  
**Maintained By:** RCA Engine Team
