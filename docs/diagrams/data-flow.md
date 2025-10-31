# Data Flow Diagrams

**Last Updated**: October 27, 2025

## Overview

This document contains sequence diagrams showing how data flows through the RCA Engine for different operations.

## 1. File Upload and Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI API
    participant DB as PostgreSQL
    participant Worker as Async Worker
    participant PII as PII Redactor
    participant Storage as File Storage

    User->>UI: Select files and upload
    UI->>API: POST /api/files/upload<br/>(multipart/form-data)
    
    API->>API: Validate file types<br/>Check size limits
    API->>Storage: Save uploaded files
    API->>DB: Create file record<br/>(metadata, path, hash)
    API->>DB: Create job record<br/>(status: pending)
    API-->>UI: Return job_id
    
    API->>Worker: Enqueue job<br/>(async task)
    Worker->>DB: Update job status<br/>(status: processing)
    
    Worker->>Storage: Read uploaded file
    Worker->>Worker: Extract text content<br/>(based on file type)
    Worker->>Worker: Chunk into segments<br/>(configurable size)
    
    Worker->>PII: Redact sensitive data<br/>(multi-pass)
    PII-->>Worker: Redacted chunks
    
    Worker->>DB: Store chunks<br/>(documents table)
    Worker->>Worker: Generate embeddings<br/>(via LLM provider)
    Worker->>DB: Store vectors<br/>(pgvector)
    
    Worker->>DB: Update job status<br/>(status: completed)
    Worker->>API: Emit progress event<br/>(SSE)
    API->>UI: Stream event<br/>("File ingestion complete")
    
    UI->>User: Show success notification
```

## 2. Analysis Request Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI API
    participant DB as PostgreSQL
    participant Worker as Async Worker
    participant Retrieval as Vector Search
    participant LLM as LLM Provider
    participant Reporter as Report Generator

    User->>UI: Click "Run Analysis"<br/>on uploaded files
    UI->>API: POST /api/jobs/analyze<br/>{file_ids, config}
    
    API->>DB: Create analysis job<br/>(status: pending)
    API-->>UI: Return job_id
    
    API->>Worker: Enqueue analysis job
    Worker->>DB: Update status<br/>(status: analyzing)
    Worker->>API: Emit event<br/>("Analysis started")
    API->>UI: SSE: "Analysis started"
    
    Worker->>Worker: Build query context<br/>(from file metadata)
    Worker->>Retrieval: Search similar chunks<br/>(pgvector similarity)
    Retrieval->>DB: Query embeddings<br/>(cosine similarity)
    DB-->>Retrieval: Relevant chunks
    Retrieval-->>Worker: Top N chunks
    
    Worker->>API: Emit event<br/>("Retrieved context")
    API->>UI: SSE: "Retrieved context"
    
    Worker->>Worker: Build LLM prompt<br/>(context + instructions)
    Worker->>LLM: Send analysis request<br/>(OpenAI/Claude/etc)
    
    Note over Worker,LLM: LLM processes logs,<br/>identifies patterns,<br/>generates insights
    
    LLM-->>Worker: Analysis response<br/>(structured JSON)
    
    Worker->>API: Emit event<br/>("LLM analysis complete")
    API->>UI: SSE: "LLM analysis complete"
    
    Worker->>Reporter: Generate report<br/>(format: markdown/html/json)
    Reporter->>Reporter: Apply templates<br/>Format sections
    Reporter-->>Worker: Formatted report
    
    Worker->>DB: Store report<br/>(jobs table)
    Worker->>DB: Update status<br/>(status: completed)
    
    Worker->>API: Emit event<br/>("Analysis completed")
    API->>UI: SSE: "Analysis completed"
    
    UI->>User: Display report<br/>Show insights
```

## 3. Real-Time Progress Streaming (SSE)

```mermaid
sequenceDiagram
    participant UI as Next.js UI
    participant API as FastAPI API
    participant EventBus as Job Event Bus
    participant Worker as Async Worker
    participant DB as PostgreSQL

    UI->>API: GET /api/jobs/{job_id}/stream<br/>(EventSource connection)
    API->>EventBus: Subscribe to job events<br/>(job_id)
    API-->>UI: SSE connection established<br/>(200 OK, text/event-stream)
    
    Note over API,UI: SSE connection remains open<br/>for real-time updates
    
    Worker->>DB: Update job progress<br/>(stage: "chunking")
    Worker->>EventBus: Publish event<br/>{type: "progress", stage: "chunking"}
    
    EventBus->>API: Notify subscribers<br/>(job_id)
    API->>UI: SSE event:<br/>data: {"type":"progress","stage":"chunking"}
    UI->>UI: Update progress UI
    
    Worker->>DB: Update progress<br/>(stage: "pii_redaction")
    Worker->>EventBus: Publish event<br/>{type: "progress", stage: "pii_redaction",<br/>details: {patterns: 5, redactions: 12}}
    
    EventBus->>API: Notify subscribers
    API->>UI: SSE event:<br/>data: {"stage":"pii_redaction","redactions":12}
    UI->>UI: Show PII stats<br/>(security badge)
    
    Worker->>DB: Update progress<br/>(stage: "embedding")
    Worker->>EventBus: Publish event<br/>{type: "progress", stage: "embedding"}
    EventBus->>API: Notify subscribers
    API->>UI: SSE event:<br/>data: {"stage":"embedding"}
    
    Worker->>DB: Update progress<br/>(stage: "analyzing")
    Worker->>EventBus: Publish event<br/>{type: "progress", stage: "analyzing"}
    EventBus->>API: Notify subscribers
    API->>UI: SSE event:<br/>data: {"stage":"analyzing"}
    
    Worker->>DB: Job complete<br/>(status: "completed")
    Worker->>EventBus: Publish event<br/>{type: "complete", report_id: "..."}
    EventBus->>API: Notify subscribers
    API->>UI: SSE event:<br/>data: {"type":"complete"}
    
    UI->>UI: Show completion<br/>Enable report view
    UI->>API: Close SSE connection
    API->>EventBus: Unsubscribe<br/>(job_id)
```

## 4. PII Redaction Workflow (Simplified)

```mermaid
sequenceDiagram
    participant Worker as Worker
    participant PII as PII Redactor
    participant Patterns as Pattern Engine
    participant Validator as Post-Validator

    Worker->>PII: Redact text<br/>(original content)
    
    Note over PII: Pass 1: Initial scan
    PII->>Patterns: Detect patterns<br/>(AWS keys, emails, SSNs, etc)
    Patterns-->>PII: Matches found (15)
    PII->>PII: Replace with tokens<br/>[REDACTED-AWS-KEY-1]
    
    Note over PII: Pass 2: Re-scan revealed text
    PII->>Patterns: Detect patterns<br/>(on redacted text)
    Patterns-->>PII: Matches found (3 more)
    PII->>PII: Replace additional patterns
    
    Note over PII: Pass 3: Final check (if enabled)
    PII->>Patterns: Final pattern scan
    Patterns-->>PII: Matches found (0)
    
    PII->>Validator: Validate redaction<br/>(check for leaks)
    Validator->>Validator: Scan for known patterns<br/>Check entropy
    Validator-->>PII: Validation result<br/>(passed: true)
    
    PII-->>Worker: Redacted text +<br/>metadata {patterns: 18,<br/>passes: 2, warnings: 0}
    
    Worker->>Worker: Emit progress event<br/>(redaction stats)
```

## Key Observations

### Upload Flow
- Files are validated before storage
- Jobs are created immediately for tracking
- Worker processes asynchronously (no blocking)
- Progress events stream to UI in real-time

### Analysis Flow
- Vector similarity search finds relevant context
- LLM provider is configurable per job
- Reports support multiple formats (Markdown, HTML, JSON)
- All stages emit progress events

### SSE Streaming
- Single persistent connection per job
- Events published by worker, consumed by API, streamed to UI
- Enables real-time progress visibility
- Connection closed when job completes

### PII Redaction
- Multi-pass approach catches nested patterns
- Post-validation ensures no leaks
- Metadata tracks redaction statistics
- Configurable number of passes (1-3)

## Related Diagrams

- [System Architecture](architecture.md) - Component overview
- [PII Pipeline](pii-pipeline.md) - Detailed PII redaction flow
- [Deployment Topology](deployment.md) - Infrastructure setup
