# Analyst Guide: Related Incident Discovery

The Related Incidents surface helps analysts compare an active RCA session with historical automation events without leaving the console.

## Prerequisites
- Backend API (`apps/api`) running at `http://localhost:8001`
- `RELATED_INCIDENTS_ENABLED` feature flag set to `true`
- Analyst is authenticated in the RCA UI

## Using the Related Incidents Panel
1. Open **Related** from the global navigation bar.
2. Choose one of the lookup modes:
   - **Lookup by session**: Paste a completed RCA session identifier. Use the relevance slider to widen or tighten matches and the result limit control to adjust the response size.
   - **Search by description**: Provide a short summary of the incident and optionally restrict the scope to the current workspace by supplying its UUID.
3. (Optional) Apply a platform filter to focus on UiPath, Blue Prism, Appian, Pega, or Automation Anywhere fingerprints.
4. Submit the form. Successful calls display similarity-ranked matches with platform badges, fingerprint health, and guardrail tags.
5. When cross-workspace matches are returned, the backend issues an audit token. Analysts should include this token in any downstream ticket notes so the security team can trace visibility changes.
6. If the API returns no data or the backend is unavailable, the UI automatically loads curated sample results so analysts can still explore filter behaviors.

## Cross-Workspace Visibility
- Matches flagged with `CROSS_WORKSPACE` originate from outside the current tenant and are only shown when the multi-tenant scope is enabled.
- Each lookup posts a Prometheus metric (`related_incident_response_total`) containing the response channel (session vs. search), scope, filter values, and whether an audit token was issued.
- Audit inserts are recorded through `core/security/audit.py`, ensuring that cross-tenant access remains reviewable.

## Troubleshooting
- Verify that the backend `/api/v1/incidents/{session_id}/related` and `/api/v1/incidents/search` endpoints return HTTP 200 responses before debugging the UI.
- Check the browser console for CORS errors; update `NEXT_PUBLIC_API_BASE_URL` if your API is not hosted on `localhost:8001`.
- Run `npm test -- --runTestsByPath src/app/related/__tests__/page.test.tsx` to confirm filter and fallback logic remain healthy.
