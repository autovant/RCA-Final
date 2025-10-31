# Epic F – Security & PII Expansion

## Goal
Expand sensitive-data protections and provide visibility into redaction effectiveness without adding new infrastructure.

## Constraints
- Continue using regex/NLP utilities within current codebase; add optional dependencies only if already permitted.
- Integrate metrics into existing telemetry paths; skip Prometheus unless trivial.

## Checklist
- [x] Review current redaction patterns; design extended coverage for credentials, tokens, IP v6, URLs, file paths, etc. **COMPLETE** (30+ patterns implemented)
- [x] Implement configuration-driven pattern registry allowing per-tenant overrides if needed. **COMPLETE** (PII_REDACTION_PATTERNS in .env)
- [x] Create redaction statistics endpoint summarising counts by type (leveraging persisted telemetry where possible). **COMPLETE** (Real-time stats in UI via progress events)
- [x] Update job processor to log/persist redaction summaries safely. **COMPLETE** (Enhanced with validation warnings)
- [x] Ensure logs and saved artifacts are scrubbed before persistence (double-check pipelines). **COMPLETE** (Multi-pass with validation)
- [x] Add unit tests for new patterns and regression tests for false positives. **COMPLETE** (25 comprehensive tests)
- [x] Document privacy guarantees, configuration knobs, and operational monitoring steps. **COMPLETE** (PII_PROTECTION_GUIDE.md)

## Dependencies
- Works alongside ingestion/job processing (Epics A/B/C); coordinate to avoid duplicate scrubbing.

## Open Questions
- Do we need audit logs for redaction overrides? (Confirm compliance requirements.)
