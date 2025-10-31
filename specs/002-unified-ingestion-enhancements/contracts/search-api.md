# Related Incidents Search API Contract

## Endpoint

`GET /api/v1/incidents/search`

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language description or session summary text |
| `scope` | enum | No | `workspace` | Search scope: `workspace`, `all_accessible`, `global` |
| `platform` | enum | No | - | Filter by platform: `blueprism`, `uipath`, `appian`, `automationanywhere`, `pega` |
| `min_relevance` | float | No | `0.60` | Minimum relevance score (0.0-1.0) |
| `limit` | integer | No | `10` | Max results to return (1-50) |
| `offset` | integer | No | `0` | Pagination offset |

## Response Schema

```json
{
  "results": [
    {
      "session_id": "uuid",
      "workspace_id": "uuid",
      "workspace_name": "string",
      "summary": "string",
      "relevance_score": 0.85,
      "platform": "blueprism",
      "created_at": "2025-10-17T10:30:00Z",
      "tags": ["timeout", "database"]
    }
  ],
  "total": 42,
  "query_time_ms": 150,
  "audit_token": "string"
}
```

## Error Responses

**400 Bad Request**:
```json
{
  "error_code": "INVALID_QUERY",
  "message": "Query text must not be empty",
  "details": {}
}
```

**403 Forbidden**:
```json
{
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "message": "Access denied to workspace: {workspace_id}",
  "details": {"workspace_id": "uuid"}
}
```

**500 Internal Server Error**:
```json
{
  "error_code": "SEARCH_SERVICE_ERROR",
  "message": "Similarity search failed",
  "details": {"retry_after_seconds": 5}
}
```

## Audit Token Usage

The `audit_token` returned in search responses MUST be included when viewing related incident details to track cross-workspace access per FR-012.

**Related Endpoint**: `GET /api/v1/incidents/{session_id}/related?audit_token={token}`

## Performance Characteristics

- **Target Latency**: p95 < 1 second (per plan.md)
- **Caching**: Results cached for 5 minutes per query signature
- **Rate Limiting**: 100 requests/minute per user
