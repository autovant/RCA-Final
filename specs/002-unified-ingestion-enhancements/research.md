# Research Summary

## Decision 1: Reuse existing pgvector embeddings for similarity fingerprints
- **Decision**: Continue storing incident embeddings and fingerprint metadata in the existing Postgres + pgvector tables, adding any missing fields (e.g., cross-workspace visibility flags) instead of introducing a new vector store.
- **Rationale**: The current ingestion pipeline already generates embeddings for RCA summaries, and pgvector supports the cosine similarity queries needed for fast related-incident lookup. Keeping the data in Postgres simplifies transactional integrity with job metadata and avoids operating additional infrastructure.
- **Alternatives considered**:
  - **Dedicated vector service (e.g., Pinecone, Weaviate)**: Rejected due to added cost, network latency, and operational overhead without clear performance benefits for the projected data volume.
  - **File-based similarity index**: Rejected because it complicates multi-tenant access control and scaling beyond a single host.

## Decision 2: Platform detection executed during ingestion job pre-processing stage
- **Decision**: Trigger platform detection and parser selection in the ingestion worker immediately after archive extraction but before fingerprint generation, persisting detection confidence and extracted entities alongside job metadata.
- **Rationale**: Performing detection early ensures downstream stages (summaries, metrics) already know the platform and can enrich outputs. It aligns with the existing job lifecycle hooks and keeps detection logic close to file validation, reducing duplicated parsing later.
- **Alternatives considered**:
  - **Client-side detection prior to upload**: Rejected because customers cannot be trusted to run uniform tooling and it would complicate UX.
  - **Deferred detection during analyst review**: Rejected because it would delay parser-driven insights and create inconsistent telemetry.

## Decision 3: Extended archive handling via Python standard library streams
- **Decision**: Support `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, and `.tar.xz` using Python's `tarfile`, `bz2`, and `lzma` modules with streaming extraction plus existing guardrails (size, member count, decompression ratio).
- **Rationale**: These modules are already available in the runtime, meeting the "no new system dependency" constraint. Streaming avoids loading entire archives in memory and preserves current watchdog limits, lowering zip-bomb risk.
- **Alternatives considered**:
  - **Third-party extraction libraries**: Rejected because they add maintenance burden and potential security issues while providing limited additional value.
  - **Limiting support to single-file `.bz2`/`.xz` without tar combinations**: Rejected because customers frequently deliver tarballs; failing to support them would negate the epic goal.

## Decision 4: Cross-workspace related-incident visibility for all analyst roles with audit trails
- **Decision**: Allow analysts who hold multi-workspace access to see related incidents across all workspaces they can query, independent of role tier, while recording audit events for each cross-workspace match review.
- **Rationale**: Aligns with clarified requirement to avoid role-based differences, simplifies UI logic, and still honors existing access controls (users must already be authorized for each workspace). Auditing mitigates compliance risk when viewing external tenant history.
- **Alternatives considered**:
  - **Restrict cross-workspace visibility to elevated roles**: Rejected per clarified scope and because it adds conditional UI complexity.
  - **Duplicate incidents into a global workspace**: Rejected due to data duplication, increased storage cost, and risk of stale copies.
