# RCA Engine Documentation

Welcome to the consolidated documentation hub for the RCA Engine. Use the sections below to ramp up quickly, deploy with confidence, and operate day-to-day.

## 🔒 Recent Security Enhancements

**Enterprise PII Protection** - The RCA Engine now features military-grade, multi-layer PII redaction with 30+ pattern types, multi-pass scanning (up to 3 passes), and strict validation to ensure **zero sensitive data leakage** to LLMs. This feature is **enabled by default** and provides real-time visibility through security badges and live stats. See the [PII Protection Guide](PII_PROTECTION_GUIDE.md) for complete details.

## Getting Started
- [Quickstart checklist](getting-started/quickstart.md)
- [Developer environment setup](getting-started/dev-setup.md)

## Deployment
- [Deployment guide](deployment/deployment-guide.md)

## Operations
- [Startup & helper scripts](operations/startup-scripts.md)
- [Job processor operations](operations/job-processor.md)
- [Troubleshooting playbook](operations/troubleshooting.md)
- [Archive handling guide](operations/archive-handling.md) ⭐ NEW
- [Archive troubleshooting](troubleshooting/archive-issues.md) ⭐ NEW
- [HTTP polling implementation](operations/HTTP_POLLING_IMPLEMENTATION.md)
- [Script consolidation plan](operations/SCRIPT_CONSOLIDATION_PLAN.md)

## Reference
- [Platform features](reference/features.md)
- [Architecture overview](reference/architecture.md)
- [Authentication guide](reference/authentication.md)
- [🔒 PII Protection & Security Guide](PII_PROTECTION_GUIDE.md) ⭐ **CRITICAL**
- [ITSM overview](reference/itsm-overview.md)
- [OpenAI provider setup](reference/openai-provider-setup.md)
- [Product requirements (PRD)](reference/prd.md)
- [Platform detection guide](reference/platform-detection.md) ⭐ NEW
- ITSM playbooks: [Integration guide](ITSM_INTEGRATION_GUIDE.md), [Quickstart](ITSM_QUICKSTART.md), [Runbook](ITSM_RUNBOOK.md)

## Reports & Validation
- [Unified Ingestion Validation](reports/unified-ingestion-validation.md) ⭐ NEW
- [Logging Security Review](reports/logging-security-review.md) ⭐ NEW
- [UI/UX Design Audit](reports/ui-ux-design-audit.md) 🎨 NEW
- [UI/UX Enhancements Final](reports/ui-ux-enhancements-final.md) 🎨 NEW - **100% Complete**
- [UI/UX Completion Summary](reports/ui-ux-completion-summary.md) 🎉 NEW
- [UI/UX Visual Report](reports/ui-ux-completion-visual.md) 🏆 NEW
- [Validation Report](reports/VALIDATION_REPORT.md)

## Testing
- [Visual Regression Testing Guide](testing/visual-regression-testing.md) 🧪 NEW - Chromatic/Percy framework
- Manual helpers: [`Feature showcase setup`](FEATURES_SHOWCASE_SETUP.md), [`Manual API tests`](../tools/manual-tests/README.md)

Historical notes, implementation diaries, and one-off fix documents now live under [`docs/archive/`](archive/README.md).
