# Epic C – Advanced Archive Handling

## Goal
Support additional compressed formats (.bz2, .xz, .tar.gz, .tar.bz2, .tar.xz) with safety checks while reusing the existing ingestion pipeline.

## Constraints
- Extend current `core.files.extraction` utilities; avoid new system-level dependencies.
- Maintain extract-time limits and resource guards consistent with current implementation.

## Checklist
- [ ] Evaluate Python standard-library support for targeted formats; identify minimal extra dependencies if absolutely required.
- [ ] Extend `ArchiveExtractor` to detect and process new formats with streaming extraction.
- [ ] Implement zip-bomb and decompression ratio safeguards for tar-based archives.
- [ ] Ensure partial extraction warnings/errors integrate with telemetry and job metadata.
- [ ] Update validation utilities to enforce supported-member checks across formats.
- [ ] Add unit tests for each new format (success + failure scenarios) and regression tests for existing `.zip`/`.gz`.
- [ ] Document supported formats, limits, and troubleshooting within docs.
- [ ] Provide rollout plan/feature flag if necessary.

## Dependencies
- Ties into Epics A/B (ingestion) and F (PII scrubbing) to ensure extracted content remains protected.

## Open Questions
- Do we need to extract multiple supported files from archives or continue with first-match strategy? (Clarify expected behaviour.)
