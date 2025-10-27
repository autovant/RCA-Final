# Design Document: Workspace Cleanup and Organization

## Context

The RCA Insight Engine repository has grown organically through rapid development, resulting in:
- **Root directory clutter**: 30+ status/completion/report markdown files mixed with actual project files
- **Test file sprawl**: 6 temporary test files (`test_*.py`) in root alongside proper tests in `tests/`
- **Verification script scatter**: `check_*.py` and `verify_*.py` files left in root after debugging sessions
- **Archive bloat**: `docs/archive/` contains 60+ files with significant duplication
- **Missing visual documentation**: No architecture diagrams, making onboarding slow
- **Inconsistent guide quality**: Some docs are outdated or contradict current implementation

**Stakeholders**: All developers working on the project, new team members onboarding, operations/DevOps teams deploying the system.

**Constraints**:
- Must not break existing functionality or workflows
- Must preserve valuable historical information
- Must maintain git history (move operations, not delete+recreate)
- Should complete in single PR to avoid partially-clean state

## Goals / Non-Goals

### Goals
1. **Clean root directory** - Remove all temporary artifacts, leaving only essential project files
2. **Organize tests properly** - Separate debug/ad-hoc tests from production test suite
3. **Create visual documentation** - Add 5 comprehensive Mermaid diagrams for architecture, flows, and workflows
4. **Consolidate archive** - Deduplicate and index historical documentation
5. **Update essential guides** - Ensure quickstart, dev-setup, and deployment guides are accurate
6. **Improve discoverability** - Clear directory structure and comprehensive index

### Non-Goals
- **Not** refactoring code or changing application behavior
- **Not** rewriting all documentation from scratch
- **Not** migrating to different documentation framework (staying with markdown)
- **Not** creating automated documentation generation (future enhancement)

## Decisions

### Decision 1: Create `tests/debug/` for Ad-Hoc Tests
**Rationale**: Developers often create temporary test files for debugging. Rather than pollute root or proper test directories, provide a dedicated space that's gitignored.

**Alternatives considered**:
- Delete all ad-hoc tests → Too aggressive, loses debugging work
- Keep in root with .gitignore → Still clutters directory listings
- Put in `scripts/` → Confuses purpose of scripts directory

**Chosen approach**: Create `tests/debug/` with .gitignore, move existing root test files there, update pytest.ini to exclude.

### Decision 2: Use Mermaid for All Diagrams
**Rationale**: Mermaid is text-based, version-controllable, renders in GitHub/VSCode, and supports multiple diagram types (flowchart, sequence, C4).

**Alternatives considered**:
- PlantUML → Less GitHub integration, extra tooling
- Draw.io/Lucidchart → Binary files, harder to version control, requires external tools
- ASCII art → Limited visual appeal, hard to maintain

**Chosen approach**: Mermaid in markdown files, with optional PNG exports in `docs/assets/diagrams/` for presentations.

### Decision 3: Archive Index vs Full Cleanup
**Rationale**: Historical fixes contain valuable context for future troubleshooting, but 60+ unorganized files is overwhelming.

**Alternatives considered**:
- Delete all archive → Loses institutional knowledge
- Keep as-is → Remains overwhelming
- Move to wiki/external → Fragments documentation

**Chosen approach**: Create `HISTORICAL_NOTES.md` index categorizing fixes, remove true duplicates, keep representative examples.

### Decision 4: Diagram Organization Structure
**Rationale**: Need clear separation between different types of diagrams while keeping them discoverable.

**Structure**:
```
docs/
├── diagrams/
│   ├── README.md                    # Hub with all diagram links
│   ├── architecture.md              # System components
│   ├── data-flow.md                 # Request flows
│   ├── deployment.md                # Infrastructure
│   ├── pii-pipeline.md              # Security flows
│   └── itsm-integration.md          # External integrations
├── assets/
│   ├── images/                      # Screenshots, photos
│   └── diagrams/                    # Exported PNG/SVG
```

### Decision 5: Script Reorganization
**Rationale**: `check_*.py` and `verify_*.py` are validation utilities, not production code or tests.

**New structure**:
```
scripts/
├── README.md                        # Documents all scripts
├── validation/                      # check_*.py, verify_*.py
├── dev/                             # Development helpers (if any)
└── ops/                             # Operational scripts (if any)
```

## Diagram Specifications

### 1. Architecture Diagram (`docs/diagrams/architecture.md`)
**Type**: Mermaid C4 or flowchart  
**Shows**:
- UI Layer (Next.js)
- API Layer (FastAPI)
- Worker Layer (Async processor)
- Database (PostgreSQL + pgvector, Redis)
- LLM Providers (GitHub Copilot, OpenAI, Anthropic, Bedrock, Ollama)
- ITSM Systems (ServiceNow, Jira)
- Monitoring (Prometheus, Grafana)

### 2. Data Flow Diagram (`docs/diagrams/data-flow.md`)
**Type**: Mermaid sequence diagram (2-3 diagrams)  
**Shows**:
- **Upload Flow**: UI → API → Storage → Worker → Embeddings → Database
- **Analysis Flow**: Request → Retrieval → LLM → Report Generation → Response
- **SSE Events**: Worker → Event Bus → API → UI (real-time updates)

### 3. Deployment Diagram (`docs/diagrams/deployment.md`)
**Type**: Mermaid flowchart/graph  
**Shows**:
- WSL 2 environment
- Docker Engine (NOT Docker Desktop)
- Container layout (PostgreSQL, Redis, optional services)
- Port mappings (5432→15432, 6379→16379, 8000, 3000)
- Network topology (Windows → WSL bridge)

### 4. PII Pipeline Diagram (`docs/diagrams/pii-pipeline.md`)
**Type**: Mermaid flowchart  
**Shows**:
- Input text entry
- Pass 1: Initial pattern detection (30+ patterns)
- Pass 2: Re-scan for revealed patterns
- Pass 3: Final validation (optional)
- Post-redaction validation
- Security warning triggers
- Output with redaction stats

### 5. ITSM Integration Diagram (`docs/diagrams/itsm-integration.md`)
**Type**: Mermaid sequence diagram (2 diagrams)  
**Shows**:
- **ServiceNow Flow**: Analysis complete → Template render → Field mapping → API call → Ticket creation
- **Jira Flow**: Analysis complete → Template render → Field mapping → API call → Issue creation
- Dry-run mode branching

## Risks / Trade-offs

### Risk: Lost Information from Archive Cleanup
**Mitigation**: 
- Create comprehensive index before deletion
- Review each file manually
- Keep representative examples of each issue type
- Archive entire current state in git history (tag before cleanup)

### Risk: Breaking Documentation Links
**Mitigation**:
- Search for all markdown link references to moved files
- Update all internal links in single commit
- Add deprecation notices in old locations (if any remain)
- Test README and docs/index.md rendering after changes

### Risk: Developers Confused by New Structure
**Mitigation**:
- Update `docs/index.md` and `README.md` prominently
- Add `scripts/README.md` documenting all utility scripts
- Include migration notes in PR description
- Post announcement in team channel (if applicable)

### Trade-off: Maintenance of Diagrams
**Consideration**: Mermaid diagrams in code can drift from implementation.  
**Acceptance**: Accept this risk; diagrams are high-level and change less frequently than code. Add note in each diagram file: "Last updated: YYYY-MM-DD" and include in quarterly doc review.

## Migration Plan

### Phase 1: Preparation (Safety)
1. Create git tag `pre-cleanup` for rollback safety
2. Backup current root directory listing: `ls -la > pre-cleanup-manifest.txt`
3. Run full test suite to establish baseline: `python -m pytest`

### Phase 2: Directory Structure
1. Create new directories:
   - `docs/diagrams/`
   - `docs/assets/images/`
   - `docs/assets/diagrams/`
   - `tests/debug/` (add to .gitignore)
   - `scripts/validation/`
2. Update `.gitignore` to exclude `tests/debug/`

### Phase 3: File Movements
1. **Move test files**: `git mv test_*.py tests/debug/`
2. **Move verification scripts**: `git mv check_*.py verify_*.py scripts/validation/`
3. **Move screenshots**: `git mv *.png docs/assets/images/`
4. **Move root status docs**: `git mv *_COMPLETE.md *_SUMMARY.md *_REPORT.md docs/archive/`
5. **Remove temp files**: `rm temp_*.py *.log`

### Phase 4: Documentation Creation
1. Create all 5 Mermaid diagram files
2. Create `docs/diagrams/README.md` index
3. Create `scripts/README.md` documenting utilities
4. Create `docs/archive/HISTORICAL_NOTES.md` index

### Phase 5: Documentation Updates
1. Update `README.md` with diagram links and cleaner structure
2. Update `docs/index.md` with new "Architecture & Diagrams" section
3. Update `docs/getting-started/quickstart.md` (verify steps)
4. Update `docs/getting-started/dev-setup.md` (verify Docker/WSL instructions)
5. Update `docs/deployment/deployment-guide.md` (add production checklist)

### Phase 6: Archive Cleanup
1. Audit `docs/archive/` for duplicates
2. Merge duplicate content into single representative files
3. Remove superseded troubleshooting docs
4. Update `docs/archive/README.md` with new index

### Phase 7: Validation
1. Run tests: `python -m pytest`
2. Check all markdown links: `npm run check-links` (if available) or manual review
3. Verify startup scripts work: `.\quick-start-dev.ps1`
4. Review diagrams render in GitHub preview
5. Get team member to review new structure

### Rollback Plan
If issues discovered:
1. `git checkout pre-cleanup` (tag created in Phase 1)
2. Create new branch to fix specific issues
3. Cherry-pick fixes back to cleanup branch

## Open Questions

1. **Should we add automated link checking to CI?**  
   → Future enhancement, not blocking cleanup

2. **Should temp files be in .gitignore from start?**  
   → Yes, add patterns: `test_*.py` in root, `tests/debug/*`, `*.log`, `temp_*.py`

3. **Do we need PNG exports of diagrams immediately?**  
   → No, Mermaid markdown is sufficient; add PNGs later if needed for presentations

4. **Should we version diagrams?**  
   → Add "Last updated" footer in each diagram file; formal versioning overkill for now

5. **How often to review diagram accuracy?**  
   → Add to quarterly documentation review checklist (create if doesn't exist)
