# Epic B – Platform Detection & Parsing

## Goal
Automatically detect RPA platform logs and extract platform-specific entities to enrich downstream analysis.

## Constraints
- Extend current ingestion and job-processing code; no new services or external dependencies beyond what the repo already uses.
- Keep detection/pluggable parsers feature-flagged for gradual rollout.

## Checklist
- [ ] Audit sample logs for Blue Prism, UiPath, Appian, Automation Anywhere, and Pega (collect fixtures for tests).
- [ ] Design detection framework (confidence scoring + metadata persistence) using existing pipeline hooks.
- [ ] Implement parser abstraction and per-platform parsers with entity extraction outputs.
- [ ] Persist extracted entities in Postgres (extend existing tables/JSON payloads where possible).
- [ ] Update job processor to branch logic based on detected platform and to include entities in summaries.
- [ ] Emit telemetry/metrics (reuse current metrics collectors) for detection confidence and parser outcomes.
- [ ] Add unit tests for detection logic and parser outputs; create integration test covering full ingestion path.
- [ ] Document parser usage, feature flags, and rollback steps.

## Dependencies
- Builds on current file ingestion flow and must align with Epic A data expectations.

## Open Questions
- Should parsers fallback to generic pipeline when confidence < threshold? (Confirm behavior.)
