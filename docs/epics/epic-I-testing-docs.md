# Epic I – Testing & Documentation Uplift

## Goal
Strengthen automated test coverage and modernise documentation to support the new feature set.

## Constraints
- Use existing pytest, coverage tooling, and documentation structure; no new CI providers.
- Keep additional dependencies minimal and vetted.

## Checklist
- [ ] Establish coverage baselines per module; set targets aligned with spec (≥70%).
- [ ] Add or expand unit/integration tests for new epics (A–H) and ensure regression coverage.
- [ ] Update pytest configuration (if needed) to include coverage reports and HTML output.
- [ ] Create smoke test scripts/playbooks for local verification.
- [ ] Refresh onboarding docs, quick start guides, and runbooks to reflect new features.
- [ ] Document feature flags, default states, and operational toggles in a central reference.
- [ ] Add changelog entries and release notes templates.
- [ ] Conduct doc QA (link checks, consistency) and capture gaps.
- [ ] Plan knowledge-sharing sessions or internal training materials as appropriate.

## Dependencies
- Dependent on completion of preceding epics to capture final behaviour.

## Open Questions
- Should we integrate automated doc validation (e.g., markdown lint) within existing tooling? (Decide once scope is clearer.)
