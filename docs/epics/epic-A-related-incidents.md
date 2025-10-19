# Epic A – Related Incidents & RAG

## Goal
Deliver historical incident discovery that surfaces similar past analyses directly within the RCA workflow.

## Constraints
- Reuse existing FastAPI services, PostgreSQL models, embeddings cache, and Next.js frontend.
- Defer Prometheus metrics unless they fall out of work being done.

## Checklist
- [ ] Inventory existing job/document schema and confirm data suitable for incident retrieval.
- [ ] Design incident index (Postgres tables + ORM) for storing similarity metadata.
- [ ] Implement similarity service using current embedding generation (fallback to vector-only while BM25 absent).
- [ ] Expose REST endpoints: `POST /api/v1/incidents/search` and `GET /api/v1/incidents/{session_id}/related`.
- [ ] Integrate lookup into job processor so completed analyses record historical fingerprints.
- [ ] Build Next.js `/related-incidents` page with filtering, platform badges, export actions.
- [ ] Add session detail panel component linking to related incidents.
- [ ] Create unit/integration tests (service + API) and component tests for UI.
- [ ] Document API usage, feature flag strategy, and rollback plan in `/docs`.

## Dependencies
- Requires embeddings generated/stored for analyses (existing pipeline).

## Open Questions
- Should similarity scoring hide low-confidence matches by default? (Decide with product.)
