# Epic D – Workflow Lifecycle & Review

## Goal
Introduce reviewer workflows (pending review → approved/rejected) with history and comments to govern RCA outputs.

## Constraints
- Extend existing `jobs` tables and FastAPI routers without introducing new services.
- Leverage current auth model; enhance only after confirming requirements.

## Checklist
- [ ] Model new job states (`pending_review`, `approved`, `rejected`) and audit history in ORM.
- [ ] Add review comment storage linked to job events.
- [ ] Create API endpoints for approve/reject actions with permission checks.
- [ ] Update job processor to transition completed analyses to `pending_review` when required.
- [ ] Extend SSE/poll endpoints to include workflow status changes.
- [ ] Build reviewer UI components (review queue, detail pane, action buttons) in Next.js.
- [ ] Add notifications or hooks (reuse existing event system) for state transitions.
- [ ] Write unit/integration tests covering state transitions and API permissions.
- [ ] Document workflow lifecycle, roles, and rollback steps.

## Dependencies
- Requires analyses to complete successfully (tie-in with Epics A/B).

## Open Questions
- Should approvals be limited to specific roles? (Clarify RBAC expectations.)
