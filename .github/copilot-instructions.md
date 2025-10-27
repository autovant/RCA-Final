# RCA-Final Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-14

## Active Technologies
- Python 3.11 (repository standard per `setup.py`) + FastAPI, SQLAlchemy, pgvector, Redis, Prometheus client, httpx, python-magic, chardet, planned additions `tiktoken` (token awareness) and PostgreSQL full-text search extensions (001-act-as-the)
- Python 3.11 (backend), TypeScript 5.x with Next.js 13 (frontend) + FastAPI, SQLAlchemy, pgvector, Redis, structlog, Next.js/React, Tailwind CSS (002-unified-ingestion-enhancements)
- PostgreSQL 15 with pgvector extension; Redis for cache/queues (002-unified-ingestion-enhancements)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (002-unified-ingestion-enhancements)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (002-unified-ingestion-enhancements)

## Project Structure
```
src/
tests/
```

## Commands
cd src; pytest; ruff check .

## Code Style
Python 3.11 (repository standard per `setup.py`): Follow standard conventions

## Recent Changes
- 002-unified-ingestion-enhancements: Added Python 3.11 (backend), TypeScript 5.x with Next.js 13 (frontend) + FastAPI, SQLAlchemy, pgvector, Redis, structlog, Next.js/React, Tailwind CSS
- 002-unified-ingestion-enhancements: Added [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
- 002-unified-ingestion-enhancements: Added Python 3.11 (backend), TypeScript 5.x with Next.js 13 (frontend) + FastAPI, SQLAlchemy, pgvector, Redis, structlog, Next.js/React, Tailwind CSS

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
