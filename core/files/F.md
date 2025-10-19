# File Upload & RAG Pipeline – Pragmatic Enhancement Plan
**Date:** 2025-10-13  
**Reviewer:** GPT-5-Codex (GitHub Copilot)  
**Scope:** RCA Log Analysis Upload → Chunking → Embedding → Retrieval  
**Goal:** Incremental reliability & cost improvements without destabilizing production.

---

## Guiding Principles
1. Protect current SLAs (≤4 min ingest for ≤20 MB files).
2. Enable metrics and rollback before each feature flag rollout.
3. Target measurable cost or latency wins per release.

---

## Phase 0 – Baseline Hardening (1 sprint)
- Instrument embed/cache/storage timings and error rates (Prometheus counters already mentioned; implement first).
- Add smoke tests covering UTF‑8/UTF‑16 and malformed files to lock today’s behaviour.
- Produce dataset of representative uploads (top 10 file types, size distribution) to validate future claims.

---

## Phase 1 – Format & Cost Quick Wins (2–3 sprints)
- Extend ingestion to `.gz` and `.zip` wrappers only; reuse existing text pipeline after extraction. Defer JSON/XML until telemetry shows need.
- Ship an opt-in embedding cache backed by existing DB (new table `embedding_cache`) but default off. Use async eviction job only after hit-rate >30%.
- Document migration/ops steps (DDL, vacuum strategy) with rollback scripts.

**Success metrics:** ≥40 % cache hit rate on pilot tenants; no increase in ingest failure rate.

---

## Phase 2 – Chunk Quality Improvements (3–4 sprints)
- Replace fixed char sizing with token-aware configuration per active model (start with GPT‑4o + Anthropic Sonnet). Use feature flag per tenant.
- Add stack-trace preservation heuristic plus guardrails preventing empty/garbled chunks; reject chunk if printable ratio <90%.
- Backfill quality metrics (`chunk_quality_score`) to confirm benefits before activating globally.

**Exit criteria:** ≥15 % reduction in LLM prompt tokens per incident with equal/higher analyst satisfaction.

---

## Phase 3 – Retrieval Enhancements (4–6 sprints)
- Introduce hybrid search (vector + keyword BM25) via existing historical store; defer cross-encoder reranking until infra cost understood.
- Add optional citation metadata in RCA responses (chunk ID + line range) to aid analyst trust.
- Monitor query latency impact; abort feature if P95 > 1.5× current baseline.

---

## Deferred / Research Topics
- Streaming >100 MB files, binary parsers (`.evtx`), Parquet/Avro: capture requirements via customer interviews first.
- Compression at rest: run storage cost study; ensure DB supports per-row compression or external blob store.
- Auto-tagging & temporal analytics: schedule after telemetry indicates repetitive incidents and analyst demand.

---

## Risk & Rollback Plan
- Every phase gated behind feature flags with clear disable switches.
- Maintain migration playbooks (schema forward/back) under `deploy/ops/`.
- Post-release reviews must include cost delta, error rate, analyst feedback.

---

## Next Actions
1. Create telemetry tickets (instrumentation + dashboards).
2. Scope ingestion quick win MVP (gzip support + tests).
3. Draft RFC for embedding cache including ops considerations.
