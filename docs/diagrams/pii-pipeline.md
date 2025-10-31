# PII Redaction Pipeline

**Last Updated**: October 27, 2025

## Overview

The RCA Engine implements **military-grade, multi-layer PII protection** to ensure no sensitive information reaches LLMs or analysis outputs. This is a critical security feature enabled by default.

## PII Redaction Flowchart

```mermaid
flowchart TD
    Start([Input Text<br/>Original Content]) --> Config{PII Redaction<br/>Enabled?}
    
    Config -->|Disabled| NoRedact[Return Original Text<br/>⚠️ Security Warning Logged]
    Config -->|Enabled| Pass1[Pass 1: Initial Scan<br/>30+ Pattern Types]
    
    Pass1 --> Detect1[Pattern Detection<br/>- AWS/Azure Keys<br/>- JWT Tokens<br/>- Database Credentials<br/>- Private Keys<br/>- Emails/SSNs<br/>- Credit Cards<br/>- IP Addresses<br/>- Phone Numbers]
    
    Detect1 --> Match1{Patterns<br/>Found?}
    Match1 -->|Yes| Redact1[Replace with Tokens<br/>[REDACTED-TYPE-N]]
    Match1 -->|No| Pass2Decision
    
    Redact1 --> RecordStats1[Record Stats<br/>- Patterns detected<br/>- Redactions made<br/>- Types found]
    RecordStats1 --> Pass2Decision{Need<br/>Pass 2?}
    
    Pass2Decision -->|Yes<br/>Patterns > 0| Pass2[Pass 2: Re-scan<br/>Check Revealed Text]
    Pass2Decision -->|No| PostValidation
    
    Pass2 --> Detect2[Scan Redacted Text<br/>Look for Nested Patterns]
    Detect2 --> Match2{New Patterns<br/>Found?}
    Match2 -->|Yes| Redact2[Redact Additional<br/>Patterns]
    Match2 -->|No| Pass3Decision
    
    Redact2 --> RecordStats2[Update Stats<br/>Increment redaction count]
    RecordStats2 --> Pass3Decision{Need<br/>Pass 3?}
    
    Pass3Decision -->|Yes<br/>Max passes = 3| Pass3[Pass 3: Final Check<br/>Paranoid Mode]
    Pass3Decision -->|No| PostValidation
    
    Pass3 --> Detect3[Final Pattern Scan<br/>Deep Inspection]
    Detect3 --> Match3{Patterns<br/>Found?}
    Match3 -->|Yes| Redact3[Redact Final Patterns<br/>Update Stats]
    Match3 -->|No| PostValidation
    
    Redact3 --> PostValidation[Post-Redaction<br/>Validation]
    
    PostValidation --> ValidateCheck{Validation<br/>Checks}
    
    ValidateCheck --> EntropyCheck[High Entropy<br/>Token Detection]
    ValidateCheck --> PatternCheck[Known Pattern<br/>Re-verification]
    ValidateCheck --> LengthCheck[Suspicious Length<br/>Analysis]
    
    EntropyCheck --> ValidationResult{All Checks<br/>Passed?}
    PatternCheck --> ValidationResult
    LengthCheck --> ValidationResult
    
    ValidationResult -->|Failed| SecurityWarn[🚨 Security Warning<br/>Potential Leak Detected]
    ValidationResult -->|Passed| MetadataGen[Generate Metadata<br/>- Total patterns: N<br/>- Redactions: M<br/>- Passes: P<br/>- Warnings: W]
    
    SecurityWarn --> FailsafeRedact[Failsafe: Over-Redact<br/>Aggressive Tokenization]
    FailsafeRedact --> LogWarning[Log Security Event<br/>Alert Monitoring]
    LogWarning --> MetadataGen
    
    MetadataGen --> EmitEvent[Emit Progress Event<br/>SSE to UI]
    EmitEvent --> Success([Return Redacted Text<br/>+ Metadata])
    
    NoRedact --> WarningEnd([Return Original<br/>⚠️ Unprotected])

    %% Styling
    classDef startEnd fill:#4caf50,stroke:#333,stroke-width:2px,color:#fff
    classDef decision fill:#ff9800,stroke:#333,stroke-width:2px,color:#000
    classDef process fill:#2196f3,stroke:#333,stroke-width:2px,color:#fff
    classDef warning fill:#f44336,stroke:#333,stroke-width:2px,color:#fff
    classDef validation fill:#9c27b0,stroke:#333,stroke-width:2px,color:#fff

    class Start,Success,WarningEnd startEnd
    class Config,Match1,Pass2Decision,Match2,Pass3Decision,Match3,ValidationResult decision
    class Pass1,Detect1,Redact1,RecordStats1,Pass2,Detect2,Redact2,RecordStats2,Pass3,Detect3,Redact3,MetadataGen,EmitEvent process
    class NoRedact,SecurityWarn,FailsafeRedact,LogWarning warning
    class PostValidation,ValidateCheck,EntropyCheck,PatternCheck,LengthCheck validation
```

## 30+ Protected Pattern Types

### Credentials & Secrets
1. **AWS Access Keys** - `AKIA[A-Z0-9]{16}`
2. **AWS Secret Keys** - `[A-Za-z0-9/+=]{40}`
3. **Azure Storage Keys** - Base64, 88 chars
4. **JWT Tokens** - `eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+`
5. **API Keys** - Generic patterns with high entropy
6. **OAuth Tokens** - Bearer tokens, access tokens
7. **Database Connection Strings** - PostgreSQL, MySQL, MongoDB, etc.
8. **Private Keys** - `-----BEGIN PRIVATE KEY-----`
9. **SSH Private Keys** - `-----BEGIN OPENSSH PRIVATE KEY-----`
10. **PGP/GPG Keys** - `-----BEGIN PGP PRIVATE KEY BLOCK-----`
11. **Passwords in URLs** - `http://user:password@host`
12. **Environment Variables** - `PASSWORD=`, `SECRET=`, `KEY=`
13. **Base64 Encoded Secrets** - High entropy base64 strings

### Personal Identifiable Information (PII)
14. **Email Addresses** - RFC 5322 compliant
15. **Phone Numbers** - US/International formats
16. **Social Security Numbers (SSN)** - `XXX-XX-XXXX`
17. **Credit Card Numbers** - Visa, MasterCard, Amex, Discover
18. **Passport Numbers** - Various country formats
19. **Driver's License Numbers** - US state formats
20. **National ID Numbers** - Multiple countries

### Network & System
21. **IPv4 Addresses** - `XXX.XXX.XXX.XXX`
22. **IPv6 Addresses** - Full and compressed formats
23. **MAC Addresses** - `XX:XX:XX:XX:XX:XX`
24. **Internal Hostnames** - Corporate DNS patterns
25. **File Paths** - `C:\Users\username\...` (Windows), `/home/username/...` (Linux)

### Business & Financial
26. **Bank Account Numbers** - IBAN, routing numbers
27. **Tax IDs** - EIN, VAT numbers
28. **Bitcoin Addresses** - `bc1...`, `1...`, `3...`
29. **Ethereum Addresses** - `0x[a-fA-F0-9]{40}`

### Custom & Contextual
30. **High Entropy Tokens** - Probabilistic detection
31. **Custom Regex Patterns** - User-configurable
32. **Context-Aware Redaction** - Nearby keywords (password, secret, token)

## Multi-Pass Strategy

### Why Multiple Passes?

Sensitive data can be **nested** or **revealed** after initial redaction:

**Example**:
```
Original: "AWS_KEY=AKIAIOSFODNN7EXAMPLE, secret=base64encodedvalue"
Pass 1:   "[REDACTED-AWS-KEY-1], secret=[REDACTED-BASE64-2]"
Pass 2:   "[REDACTED-AWS-KEY-1], [REDACTED-ENV-VAR-3]"
          ^^^^^^^^^^^^^^^^^^^^^^ "secret=" now exposed as env var
```

### Pass Configuration

| Pass | Purpose | When Executed |
|------|---------|---------------|
| 1 | Initial detection | Always |
| 2 | Re-scan revealed text | If Pass 1 found patterns |
| 3 | Paranoid final check | Optional (configurable) |

## Post-Redaction Validation

### Validation Checks

1. **Pattern Re-verification**
   - Re-run all pattern matchers on redacted text
   - Should return zero matches

2. **High Entropy Detection**
   - Calculate Shannon entropy of remaining tokens
   - Flag tokens with entropy > threshold (e.g., 4.5 bits/char)

3. **Suspicious Length Analysis**
   - Identify unusually long alphanumeric sequences
   - Cross-reference with known secret lengths

4. **Keyword Proximity**
   - Check for unredacted text near keywords like "password", "secret", "key"

### Failsafe Mechanism

If validation detects potential leaks:
```
1. Log SECURITY WARNING with details
2. Apply aggressive over-redaction
3. Replace suspicious tokens with [REDACTED-FAILSAFE-N]
4. Emit warning event to UI (🚨 security badge)
5. Continue processing (fail-safe, not fail-stop)
```

## Redaction Metadata

Each redaction operation returns:
```json
{
  "redacted_text": "[REDACTED-AWS-KEY-1] logged in",
  "stats": {
    "total_patterns_detected": 15,
    "total_redactions": 15,
    "passes_executed": 2,
    "validation_passed": true,
    "security_warnings": 0,
    "pattern_types": {
      "aws_access_key": 1,
      "email": 3,
      "ipv4_address": 2,
      "jwt_token": 1,
      "env_var": 8
    }
  },
  "enabled": true
}
```

## UI Visibility

### Real-Time Stats Display

The UI shows redaction statistics during analysis:
- **Patterns Detected**: 15 sensitive items found
- **Redactions Applied**: 15 items protected
- **Security Status**: ✅ Passed validation
- **Types**: AWS Keys (1), Emails (3), IP Addresses (2), ...

### Security Badge

- **Green ✅**: Redaction passed, no warnings
- **Yellow ⚠️**: Minor warnings (high entropy tokens detected)
- **Red 🚨**: Security warnings (potential leaks detected, failsafe applied)

## Configuration

### Feature Flag

```python
# core/config.py
class Settings(BaseSettings):
    ENABLE_PII_REDACTION: bool = True  # Default: enabled
    PII_MAX_PASSES: int = 2  # 1-3 passes
    PII_ENABLE_VALIDATION: bool = True  # Post-redaction validation
    PII_FAILSAFE_ON_WARNING: bool = True  # Apply failsafe if warnings
```

### Disable Redaction (Not Recommended)

```bash
# .env file
ENABLE_PII_REDACTION=false
```

**⚠️ Warning**: Disabling PII redaction exposes sensitive data to LLMs. Only disable in isolated test environments.

## Performance Considerations

- **Single-pass**: ~50ms for 10KB text
- **Multi-pass (2)**: ~100ms for 10KB text
- **Validation**: +20-30ms
- **Overall impact**: Minimal (<200ms for most documents)

## Audit Trail

All redactions are logged:
```
[INFO] PII redaction complete: 15 patterns detected, 2 passes, validation passed
[WARN] High entropy token detected in position 1234-1250 (failsafe applied)
[ERROR] Validation failed: known pattern still present after redaction
```

Logs include:
- Job ID
- File ID
- Redaction stats
- Validation results
- Security warnings

## Related Documentation

- [PII Protection Guide](../PII_PROTECTION_GUIDE.md) - Comprehensive security documentation
- [Data Flow](data-flow.md) - How PII redaction fits in the pipeline
- [System Architecture](architecture.md) - Security layer overview
