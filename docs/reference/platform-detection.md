# Platform Detection Reference

## Overview

The RCA platform detection system automatically identifies RPA and BPM platforms from uploaded log files and extracts platform-specific entities. This enables targeted analysis and better root cause identification by understanding the automation platform context.

## Supported Platforms

| Platform | Detection Method | Entity Types |
|----------|-----------------|--------------|
| **Blue Prism** | Heuristic scoring | Process, Session, Stage, Error |
| **UiPath** | Heuristic scoring | Workflow, Robot, Execution, Queue, Error |
| **Appian** | Heuristic scoring | Process Model, Task, User, Instance, Error |
| **Automation Anywhere** | Heuristic scoring | Bot, Task, Bot Runner, Device, Error |
| **Pega** | Heuristic scoring | Case, Flow, Ruleset, Operator, Error |

## Detection Process

### 1. Heuristic Scoring

Platform detection uses pattern matching to identify platform-specific signatures in log files:

```python
# Example Blue Prism signatures
patterns = {
    "INFO": r"\bINFO\s+Blue\s*Prism",
    "Process": r"Process:\s*'([^']+)'",
    "Stage": r"Stage:\s*'([^']+)'",
}
```

Each matched pattern contributes to a platform's confidence score. The platform with the highest score above the minimum threshold is selected.

### 2. Confidence Thresholds

| Threshold | Value | Purpose |
|-----------|-------|---------|
| **MIN_CONFIDENCE** | 0.15 | Minimum score required for platform detection |
| **ROLLOUT_CONFIDENCE** | 0.65 | Minimum score required to execute platform parser |

**Detection Behavior:**
- Score < 0.15: No platform detected (`unknown`)
- 0.15 ≤ Score < 0.65: Platform detected, parser NOT executed
- Score ≥ 0.65: Platform detected, parser executed to extract entities

### 3. Parser Execution

When confidence meets the rollout threshold, a platform-specific parser extracts structured entities:

```json
{
  "detected_platform": "blue_prism",
  "confidence_score": 0.75,
  "parser_executed": true,
  "extracted_entities": [
    {
      "entity_type": "process",
      "value": "Invoice_Processing",
      "source_file": "process_log_2024.txt"
    },
    {
      "entity_type": "error",
      "value": "Failed to connect to database",
      "source_file": "error_log.txt"
    }
  ]
}
```

## Feature Flags

Platform detection respects feature flag configuration:

```python
{
  "PLATFORM_DETECTION_ENABLED": True,  # Master switch
  "ROLLOUT_CONFIDENCE_THRESHOLD": 0.65,  # Parser execution threshold
  "DETECTION_TIMEOUT_SECONDS": 30.0  # Parser execution timeout
}
```

### Flag Behavior

| Flag State | Detection | Parser Execution |
|------------|-----------|------------------|
| `ENABLED=False` | Skipped | Skipped |
| `ENABLED=True, Score < 0.65` | Performed | Skipped |
| `ENABLED=True, Score ≥ 0.65` | Performed | Executed |

## API Access

### Get Platform Detection Results

```http
GET /api/v1/jobs/{job_id}/platform-detection
```

**Response:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "detected_platform": "uipath",
  "confidence_score": 0.82,
  "detection_method": "heuristic",
  "parser_executed": true,
  "parser_version": "1.0.0",
  "extracted_entities": [
    {
      "entity_type": "workflow",
      "value": "MainWorkflow",
      "source_file": "robot_log.txt"
    }
  ],
  "feature_flag_snapshot": {
    "PLATFORM_DETECTION_ENABLED": true,
    "ROLLOUT_CONFIDENCE_THRESHOLD": 0.65
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK`: Detection data available
- `404 Not Found`: No detection performed for this job
- `500 Internal Server Error`: Detection failed

## UI Integration

Platform detection results display in the investigation page when a job is active:

### Platform Badge
Shows the detected platform with color coding:
- Blue Prism: Blue
- UiPath: Orange
- Appian: Purple
- Automation Anywhere: Red
- Pega: Green

### Confidence Bar
Visual progress bar showing detection confidence percentage.

### Extracted Entities
Entities grouped by type (process, workflow, bot, error, etc.) displayed as tags.

## Parser Architecture

### Base Parser Interface

All platform parsers implement the `PlatformParser` abstract base class:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ParserResult:
    success: bool
    entities: List[Dict[str, str]]
    warnings: List[str]
    error: Optional[str]
    duration_ms: Optional[float]

class PlatformParser(ABC):
    @abstractmethod
    async def parse(
        self, 
        detection_input: DetectionInput, 
        timeout: Optional[float] = None
    ) -> ParserResult:
        """Extract platform-specific entities from files"""
        pass
```

### Entity Structure

Each extracted entity contains:
- `entity_type`: Category (process, workflow, bot, error, etc.)
- `value`: Extracted value (process name, error message, etc.)
- `source_file`: File where entity was found

### Adding New Parsers

1. Create parser class in `core/files/platforms/`:
```python
class MyPlatformParser(PlatformParser):
    async def parse(self, detection_input, timeout=None):
        # Implement extraction logic
        pass
```

2. Register in `core/files/platforms/registry.py`:
```python
_PARSER_REGISTRY = {
    "my_platform": MyPlatformParser(),
}
```

3. Add platform to enum in `core/db/models.py`:
```python
class RpaPlatform(str, Enum):
    MY_PLATFORM = "my_platform"
```

## Troubleshooting

### No Platform Detected

**Symptoms:** `detected_platform: "unknown"`

**Causes:**
- Log files don't contain platform-specific signatures
- Files are binary or not text-based
- Confidence score below 0.15 threshold

**Solution:**
- Verify log files contain platform identifiers
- Check file content is readable text
- Review detection patterns in `core/files/detection.py`

### Parser Not Executing

**Symptoms:** `parser_executed: false` despite platform detection

**Causes:**
- Confidence score below 0.65 rollout threshold
- Feature flag `PLATFORM_DETECTION_ENABLED` is false
- Parser execution timeout

**Solution:**
- Check `confidence_score` in detection results
- Verify feature flags in database/config
- Review logs for timeout errors
- Increase `DETECTION_TIMEOUT_SECONDS` if needed

### Missing Entities

**Symptoms:** `extracted_entities: []` when parser executed

**Causes:**
- Log format doesn't match expected patterns
- Entities are present but not captured by regex
- Files contain only generic log messages

**Solution:**
- Review parser patterns in `core/files/platforms/<platform>.py`
- Add new patterns for additional entity types
- Test regex patterns against sample logs
- Check source files for expected content

### Performance Issues

**Symptoms:** Detection takes too long or times out

**Causes:**
- Very large log files (>100MB)
- Complex regex patterns
- Timeout threshold too low

**Solution:**
- Split large files before upload
- Optimize regex patterns (avoid backtracking)
- Increase `DETECTION_TIMEOUT_SECONDS`
- Review telemetry for slow operations

## Telemetry & Monitoring

Platform detection emits structured logs and metrics:

### Metrics
- `platform_detection.duration_ms`: Detection execution time
- `platform_detection.confidence`: Confidence scores
- `parser.execution_count`: Parser execution count
- `parser.entity_count`: Extracted entity counts

### Logs
```json
{
  "event": "platform_detection_complete",
  "job_id": "...",
  "detected_platform": "uipath",
  "confidence_score": 0.75,
  "parser_executed": true,
  "entity_count": 12,
  "duration_ms": 245.7
}
```

## Best Practices

1. **Upload Quality Logs**: Ensure log files are complete and properly formatted
2. **File Organization**: Group related files (process logs, error logs) together
3. **Feature Flag Management**: Test new parsers with low rollout thresholds before production
4. **Monitor Confidence**: Review detection accuracy and adjust thresholds as needed
5. **Entity Validation**: Verify extracted entities match expected values
6. **Performance Testing**: Test with representative file sizes before production use

## Related Documentation

- [Unified Ingestion Enhancements](../specs/002-unified-ingestion-enhancements/README.md)
- [Job Processing Pipeline](./job-processing.md)
- [File Upload Guide](../getting-started/file-upload.md)
- [API Reference](./api-reference.md)
