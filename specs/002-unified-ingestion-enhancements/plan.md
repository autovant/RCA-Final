# Implementation Plan: Unified Ingestion Intelligence Enhancements

**Branch**: `[002-unified-ingestion-enhancements]` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Deliver cross-workspace related incident discovery, platform-aware log parsing, and safe archive ingestion by extending existing FastAPI ingestion services, Postgres/pgvector storage, and the Next.js analyst UI while reinforcing telemetry and safeguard coverage identified in research.md.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x with Next.js 13 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy, pgvector, Redis, structlog, Next.js/React, Tailwind CSS  
**Storage**: PostgreSQL 15 with pgvector extension; Redis for cache/queues  
**Testing**: pytest + pytest-asyncio, pytest-cov, Playwright/React Testing Library for UI  
**Target Platform**: Containerized Linux services orchestrated via Docker Compose  
**Project Type**: Web application with shared backend + frontend codebases  
**Performance Goals**: Fingerprint indexing <2 minutes p95; similarity query response <1 second p95; platform detection throughput 500 jobs/hour baseline  
**Constraints**: Maintain existing resource guardrails for archive extraction; no additional external dependencies; multi-tenant data isolation controls remain intact  
**Scale/Scope**: Tens of thousands of historical incidents per tenant; up to hundreds of concurrent ingestion jobs across tenants

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Resilience by Design**: No new external ITSM integrations introduced; reuse existing retry-capable internal services → PASS
- **Schema-First Validation**: Archive/member validation enhancements extend existing utilities; plan maintains schema checks before persistence → PASS
- **Template-Driven Ticket Creation**: Not in scope → PASS (N/A)
- **Metrics-First Integration**: Plan includes telemetry expansion for detection and archive safeguards leveraging existing Prometheus exporters. Metrics exposed via `/metrics` endpoint in OpenMetrics format per Constitution IV. New metrics: `itsm_platform_detection_total{platform, outcome}`, `itsm_archive_extraction_safeguard_violations_total{format, reason}`, `itsm_fingerprint_generation_duration_seconds{outcome}` → PASS
- **Test Coverage for Integration Paths**: Unit and integration tests required for new ingestion flows and safeguards → PASS

Post-Phase1 Review (2025-10-17): All gates remain satisfied; new telemetry counters and validation rules align with constitution standards.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── apps/
│   ├── api/                # FastAPI services, ingestion endpoints
│   └── worker/             # Background job processor
├── core/
│   ├── files/              # Archive utilities and validation
│   ├── jobs/               # Job orchestration and fingerprint logic
│   ├── llm/                # Embedding and similarity helpers
│   ├── metrics/            # Prometheus collectors
│   └── security/           # Multi-tenant access controls
└── tests/
  ├── integration/
  └── unit/

frontend/
├── ui/
│   ├── app/                # Next.js routes including related-incidents view
│   ├── components/         # Shared UI components
│   ├── lib/                # Client-side services/APIs
│   └── styles/             # Tailwind configuration
└── ui/tests/               # Component and e2e coverage
```

**Structure Decision**: Unified backend (apps/core) with dedicated Next.js frontend (`ui`) enables coordinated ingestion and analyst experience updates while keeping existing repo conventions.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_    | —          | —                                   |

````
│   ├── metrics/            # Prometheus collectors
│   └── security/           # Multi-tenant access controls
└── tests/
  ├── integration/
  └── unit/

frontend/
├── ui/
│   ├── app/                # Next.js routes including related-incidents view
│   ├── components/         # Shared UI components
│   ├── lib/                # Client-side services/APIs
│   └── styles/             # Tailwind configuration
└── ui/tests/               # Component and e2e coverage
```
| Violation | Why Needed | Simpler Alternative Rejected Because |
