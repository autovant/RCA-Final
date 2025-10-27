# Workspace Cleanup and Organization

## Why

The repository has accumulated significant technical debt from rapid development cycles, including:
- **56+ status/completion/report documents** scattered across root and docs/
- **Duplicate test files** in both root and tests/ directories (6 test files: `test_config_direct.py`, `test_fresh_import.py`, `test_getattr.py`, etc.)
- **Temporary verification scripts** (`check_*.py`, `verify_*.py`, `temp_*.py`) left in root
- **Redundant archive documentation** in docs/archive/ that duplicates information
- **Missing visual documentation** - no Mermaid diagrams for architecture, data flow, or workflows
- **Outdated and contradictory guides** spread across multiple directories
- **Poor organization** - critical docs mixed with status reports at repository root

This creates confusion for developers, makes onboarding difficult, and obscures the actual codebase structure. The workspace needs systematic cleanup and reorganization to improve maintainability and developer experience.

## What Changes

### 1. Root Directory Cleanup
- **REMOVE** all status/completion documents from root:
  - `*_COMPLETE.md` (11 files: PROJECT_COMPLETE.md, DEPLOYMENT_COMPLETE.md, etc.)
  - `*_SUMMARY.md` (3 files: TESTING_SUMMARY.md, OPTIMIZATIONS_IMPLEMENTATION_SUMMARY.md, etc.)
  - `*_REPORT.md` (3 files: BROWSER_TEST_REPORT.md, DEMO_READINESS_REPORT.md, FEATURE_FLAGS_TEST_REPORT.md)
  - `INTEGRATION_SUCCESS.md`, `RCA_REPORT_IMPROVEMENTS.md`
- **REMOVE** temporary test/verification files from root:
  - `test_*.py` (6 files: test_config_direct.py, test_fresh_import.py, test_getattr.py, test_integrated_features.py, test_minimal_pydantic.py, test_pydantic_simple.py)
  - `check_*.py` (3 files: check_class_end.py, check_fields_in_ast.py, check_flags.py)
  - `verify_*.py` (2 files: verify_flags.py, verify_integration.py)
  - `temp_*.py` (temp_head_processor.py)
- **REMOVE** obsolete log files: `test-upload.log`, `test-upload-2.log`
- **REMOVE** screenshot files: `features-page-screenshot.png`, `pii-demo-active.png` (move to docs/assets/)

### 2. Documentation Reorganization
- **CONSOLIDATE** archive documentation:
  - Audit docs/archive/ (60+ files) and remove true duplicates
  - Create single `docs/archive/HISTORICAL_NOTES.md` index referencing key fixes
  - Delete obsolete troubleshooting docs superseded by current guides
- **UPDATE** essential guides with current information:
  - `docs/getting-started/quickstart.md` - verify all steps work
  - `docs/getting-started/dev-setup.md` - confirm Docker/WSL instructions
  - `docs/deployment/deployment-guide.md` - add production checklist
  - `docs/operations/troubleshooting.md` - consolidate common issues
- **CREATE** comprehensive Mermaid diagrams:
  - `docs/diagrams/architecture.md` - System architecture with components
  - `docs/diagrams/data-flow.md` - Request flow through ingestion → analysis → output
  - `docs/diagrams/deployment.md` - Deployment topology (WSL, Docker, services)
  - `docs/diagrams/pii-pipeline.md` - Multi-pass PII redaction flow
  - `docs/diagrams/itsm-integration.md` - ServiceNow/Jira ticket workflows

### 3. Code Organization
- **MOVE** scattered test files to proper locations:
  - Root test_*.py → `tests/debug/` (create directory)
  - Root check_*.py, verify_*.py → `scripts/validation/`
- **REMOVE** unused dependencies from requirements.txt (if any identified)
- **CREATE** `scripts/README.md` documenting all utility scripts

### 4. Assets Management
- **CREATE** `docs/assets/` directory
- **MOVE** screenshots and images to `docs/assets/images/`
- **CREATE** `docs/assets/diagrams/` for exported diagram PNGs

### 5. Documentation Index Updates
- **UPDATE** `README.md` with cleaner structure and diagram links
- **UPDATE** `docs/index.md` to reference new diagram section
- **CREATE** `docs/diagrams/README.md` as diagram hub

## Impact

### Affected Specs
- **NEW**: `workspace-organization` - Establishes requirements for repository structure, documentation organization, and visual documentation

### Affected Code
- **Root directory** - Remove 30+ temporary/status files
- **docs/** - Restructure archive, add diagrams directory
- **docs/index.md** - Add diagram references
- **README.md** - Streamline with diagram links
- **tests/** - Add debug/ subdirectory for ad-hoc tests
- **scripts/** - Add validation/ subdirectory for check scripts

### Breaking Changes
None. All changes are organizational and do not affect runtime behavior.

### Migration Notes
- Developers with open branches referencing removed status docs should update links to docs/archive/
- Any scripts referencing root-level test files must update paths to tests/debug/
- Screenshot references in docs must update to docs/assets/images/

### Benefits
- **Improved discoverability** - Clear separation of code, docs, and temporary artifacts
- **Better onboarding** - Visual diagrams accelerate understanding
- **Reduced confusion** - Single source of truth for setup and operations
- **Professional appearance** - Clean root directory shows mature project
- **Easier maintenance** - Logical organization simplifies updates
