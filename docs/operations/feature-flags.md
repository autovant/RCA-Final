# Feature Flag Rollout Notes

The RCA engine exposes feature toggles through environment variables managed by `core.config.Settings`. Use this document to coordinate rollouts, track defaults, and understand cross-workspace visibility auditing impacts.

## Related Incidents Discovery

- **Environment Variable**: `RELATED_INCIDENTS_ENABLED`
- **Default**: `true`
- **Purpose**: Enables cross-workspace similarity search results in analyst workflows.
- **Rollout Guidance**:
  - Leave enabled in all lower environments to validate the new API and UI flows.
  - For regulated tenants, capture explicit approval before enabling multi-workspace visibility.
  - Pair launch with the new audit event processing (see "Cross-Workspace Visibility Auditing").
  - Ensure UI clients forward the `audit_token` returned by the API when logging cross-workspace views (Quickstart §5).

## Platform Detection & Parsers

- **Environment Variable**: `PLATFORM_DETECTION_ENABLED`
- **Default**: `true`
- **Purpose**: Activates ingestion-time heuristics and ML-assisted detectors that identify RPA platform types and run platform-specific parsers.
- **Rollout Guidance**:
  - Toggle off temporarily when onboarding a new platform to allow ingestion without parser errors.
  - Coordinate with job processor deployments because the worker now invokes detection logic in the post-extraction stage.

## Expanded Archive Formats

- **Environment Variable**: `ARCHIVE_EXPANDED_FORMATS_ENABLED`
- **Default**: `true`
- **Purpose**: Allows handling of `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, and `.tar.xz` uploads with guardrails.
- **Rollout Guidance**:
  - Keep enabled in development to ensure validation coverage for added formats.
  - Disable only if new guardrail checks surface false positives blocking mission-critical uploads; log a ticket before changing production defaults.

## Cross-Workspace Visibility Auditing

When `RELATED_INCIDENTS_ENABLED` is active, the API records `AnalystAuditEvent` entries for each cross-workspace incident view. Operations should:

1. Ensure database migrations introducing the `AnalystAuditEvent` extension table have been applied (Phase 2 tasks).
2. Monitor the audit table or associated dashboards weekly to confirm analysts only access approved workspaces.
3. Update tenant onboarding checklists to review audit retention policies (defaults to standard data retention windows).
4. Verify that downstream services ingest the `audit_token` emitted by `/incidents/search` and `/incidents/{session_id}/related` requests to preserve traceability.

## Operational Checklist

- [ ] Confirm the `.env` or deployment secret store contains explicit values for the three feature flags (even if `true`) for consistent configuration management.
- [ ] Notify the security/compliance team before enabling cross-workspace visibility in production.
- [ ] Coordinate deployments so worker pods pick up `PLATFORM_DETECTION_ENABLED` at the same time as the API layer.
- [ ] Capture guardrail anomalies from archive handling in `ArchiveExtractionAudit` for follow-up during the first week of rollout.

## Threshold Overrides & Safeguards

Fine-tune rollout thresholds and guardrails via the following environment variables exposed in `core.config.Settings`:

- `RELATED_INCIDENTS_MIN_RELEVANCE` (default `0.6`): baseline similarity score for related incident queries.
- `RELATED_INCIDENTS_MAX_RESULTS` (default `20`): cap on incidents returned per request.
- `PLATFORM_DETECTION_ROLLOUT_CONFIDENCE` (default `0.65`): confidence required before executing platform-specific parsers.
- `PLATFORM_DETECTION_PARSER_TIMEOUT_SECONDS` (default `120`): timeout applied to platform parser executions.
- `ARCHIVE_GUARDRAIL_MAX_DECOMPRESSION_RATIO` (default `250.0`): maximum permissible expansion ratio before blocking extraction.
- `ARCHIVE_GUARDRAIL_MAX_MEMBER_COUNT` (default `1000`): maximum archive member count processed during ingestion.
- `ARCHIVE_GUARDRAIL_MEMBER_SAMPLE_LIMIT` (default `25`): number of blocked members retained for auditing.
- `ARCHIVE_GUARDRAIL_EXTRACTION_TIMEOUT_SECONDS` (default `180`): fail-safe timeout for archive extraction tasks.
