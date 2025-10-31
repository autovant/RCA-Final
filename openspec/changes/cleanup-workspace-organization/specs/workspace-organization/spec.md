# Workspace Organization Specification

## ADDED Requirements

### Requirement: Root Directory Structure
The repository root directory SHALL maintain a clean, professional structure containing only essential project files and directories.

#### Scenario: Developer opens repository
- **WHEN** a developer clones or opens the repository
- **THEN** the root directory contains only:
  - Core config files (.env, .gitignore, alembic.ini, pytest.ini, requirements.txt, setup.py, docker-compose.dev.yml)
  - Shell scripts (*.ps1, *.sh)
  - README.md and AGENTS.md
  - Standard directories (apps/, core/, docs/, tests/, scripts/, etc.)
  - No temporary test files, status reports, or screenshots

#### Scenario: Status document created during development
- **WHEN** a developer creates a status/completion document during feature development
- **THEN** the document is placed in `docs/reports/` or `docs/archive/` (not repository root)

### Requirement: Test File Organization
Test files SHALL be organized by purpose and scope within the tests/ directory.

#### Scenario: Unit test created
- **WHEN** a developer writes a unit or integration test
- **THEN** the test file is placed in `tests/` with appropriate subdirectory (`unit/`, `integration/`)

#### Scenario: Debug or ad-hoc test created
- **WHEN** a developer creates a temporary test for debugging
- **THEN** the test file is placed in `tests/debug/` (gitignored)
- **AND** the file is removed after debugging is complete or moved to proper test directory if valuable

### Requirement: Documentation Visual Diagrams
The documentation SHALL include Mermaid diagrams for all critical system workflows and architecture.

#### Scenario: Developer needs architecture overview
- **WHEN** a developer reads `docs/diagrams/architecture.md`
- **THEN** they see a Mermaid diagram showing:
  - FastAPI application layer
  - Async worker layer
  - Database (PostgreSQL + pgvector)
  - LLM provider integrations
  - ITSM integrations
  - Monitoring stack (Prometheus, Grafana)

#### Scenario: Developer needs to understand request flow
- **WHEN** a developer reads `docs/diagrams/data-flow.md`
- **THEN** they see sequence diagrams showing:
  - File upload → ingestion → chunking → embedding → storage
  - Analysis request → retrieval → LLM orchestration → report generation
  - SSE streaming progress events

#### Scenario: Developer needs deployment architecture
- **WHEN** a developer reads `docs/diagrams/deployment.md`
- **THEN** they see deployment topology showing:
  - WSL 2 + Docker Engine setup
  - Container orchestration (docker-compose)
  - Network configuration (ports, proxies)
  - Service dependencies

#### Scenario: Developer needs PII protection flow
- **WHEN** a developer reads `docs/diagrams/pii-pipeline.md`
- **THEN** they see flowchart showing:
  - Multi-pass redaction stages (1-3 passes)
  - Pattern detection (30+ types)
  - Post-redaction validation
  - Security warning triggers

#### Scenario: Developer needs ITSM integration flow
- **WHEN** a developer reads `docs/diagrams/itsm-integration.md`
- **THEN** they see workflow diagrams for:
  - ServiceNow ticket creation and updates
  - Jira issue creation and field mapping
  - Custom field configuration
  - Dry-run vs production modes

### Requirement: Documentation Archive Management
Historical documentation SHALL be organized and deduplicated within docs/archive/.

#### Scenario: Developer searches for historical fix
- **WHEN** a developer looks in `docs/archive/`
- **THEN** they find a `HISTORICAL_NOTES.md` index categorizing fixes by:
  - Database connection issues
  - WSL networking fixes
  - Port configuration changes
  - Docker setup resolutions
  - UI/API routing fixes

#### Scenario: Duplicate documentation detected
- **WHEN** two archive documents describe the same fix
- **THEN** the most complete version is retained
- **AND** the duplicate is removed
- **AND** any unique information is merged into the retained document

### Requirement: Script Organization
Utility scripts SHALL be organized by purpose with clear documentation.

#### Scenario: Developer needs validation script
- **WHEN** a developer looks for check/verify scripts
- **THEN** they find scripts in `scripts/validation/` with descriptive names
- **AND** `scripts/README.md` documents each script's purpose and usage

#### Scenario: Developer needs development helper
- **WHEN** a developer looks for dev scripts
- **THEN** they find startup/stop scripts documented in `scripts/README.md`
- **AND** the README explains when to use each script (e.g., `quick-start-dev.ps1` vs `start-dev.ps1`)

### Requirement: Asset Management
Documentation assets SHALL be organized in dedicated directories by type.

#### Scenario: Developer adds screenshot to documentation
- **WHEN** a developer creates a screenshot for documentation
- **THEN** the image is saved to `docs/assets/images/`
- **AND** referenced in markdown with relative path: `![caption](../assets/images/filename.png)`

#### Scenario: Developer exports Mermaid diagram
- **WHEN** a developer exports a diagram to PNG/SVG
- **THEN** the file is saved to `docs/assets/diagrams/`
- **AND** the source Mermaid code remains in the markdown diagram file

### Requirement: Documentation Index
The documentation index SHALL provide clear navigation to all guides and diagrams.

#### Scenario: New developer onboards
- **WHEN** a new developer opens `docs/index.md`
- **THEN** they see sections for:
  - Getting Started (quickstart, dev setup)
  - Architecture & Diagrams (new section)
  - Deployment
  - Operations
  - Reference
  - Testing
- **AND** each section has 2-5 key links (not overwhelming lists)

#### Scenario: Developer needs visual reference
- **WHEN** a developer clicks the "Architecture & Diagrams" section
- **THEN** they see links to:
  - System Architecture
  - Data Flow
  - Deployment Topology
  - PII Pipeline
  - ITSM Integration
- **AND** each link includes a brief description

### Requirement: Root README Structure
The root README.md SHALL provide a concise overview with links to detailed docs and diagrams.

#### Scenario: Developer reads README
- **WHEN** a developer opens README.md
- **THEN** they see within first 100 lines:
  - Project purpose and key features (with PII protection highlight)
  - Quick links section with documentation and diagrams
  - Local development quickstart
  - Architecture diagram link
  - Repository structure map

#### Scenario: Developer needs architecture at a glance
- **WHEN** a developer scrolls to repository map section
- **THEN** they see a text-based directory structure
- **AND** a link to the full architecture diagram
