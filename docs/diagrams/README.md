# RCA Engine Diagrams

Welcome to the visual documentation hub for the RCA Insight Engine. These diagrams provide comprehensive overviews of the system architecture, data flows, and key workflows.

## 📐 Available Diagrams

### [System Architecture](architecture.md)
High-level overview of all system components, layers, and integrations.
- UI Layer (Next.js frontend)
- API Layer (FastAPI application)
- Worker Layer (async job processor)
- Database layer (PostgreSQL + pgvector, Redis)
- LLM provider integrations
- ITSM system connections
- Monitoring stack

### [Data Flow](data-flow.md)
Sequence diagrams showing how data moves through the system.
- **Upload Flow**: File ingestion → chunking → embedding → storage
- **Analysis Flow**: Request → retrieval → LLM orchestration → report generation
- **SSE Streaming**: Real-time progress updates from worker to UI

### [Deployment Topology](deployment.md)
Infrastructure and deployment architecture.
- WSL 2 environment setup
- Docker Engine configuration (NOT Docker Desktop)
- Container orchestration
- Port mappings and network topology
- Service dependencies

### [PII Redaction Pipeline](pii-pipeline.md)
Multi-pass PII protection workflow.
- Input text processing
- Pattern detection (30+ types)
- Multi-pass scanning (1-3 passes)
- Post-redaction validation
- Security warning triggers

### [ITSM Integration](itsm-integration.md)
Ticket creation workflows for external systems.
- ServiceNow ticket creation and updates
- Jira issue creation and field mapping
- Custom field configuration
- Dry-run vs production modes

## 🎨 Diagram Formats

All diagrams are created using **Mermaid**, a text-based diagramming tool that:
- ✅ Renders directly in GitHub, VS Code, and documentation sites
- ✅ Is version-controllable (no binary files)
- ✅ Can be easily updated and maintained
- ✅ Supports export to PNG/SVG for presentations

## 📅 Maintenance

**Last Updated**: October 27, 2025

These diagrams represent the current architecture as of the update date. For the most accurate information, always refer to the source code and documentation guides.

**Review Schedule**: Quarterly (or after major architectural changes)

## 🔗 Related Documentation

- [Architecture Overview](../reference/architecture.md) - Text-based architecture description
- [Developer Setup](../getting-started/dev-setup.md) - Local environment configuration
- [Deployment Guide](../deployment/deployment-guide.md) - Production deployment instructions
