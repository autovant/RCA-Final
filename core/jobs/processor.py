"""
Job processor responsible for ingesting uploaded artefacts, generating
embeddings, and orchestrating LLM-backed analysis.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import Document, File, Job
from core.jobs.service import JobService
from core.llm.embeddings import EmbeddingService
from core.llm.providers import LLMMessage, LLMProviderFactory
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FileDescriptor:
    """Snapshot of a file record detached from the ORM session."""

    id: str
    path: str
    name: str
    checksum: str
    content_type: Optional[str]
    metadata: Optional[Dict[str, Any]]
    size_bytes: int


@dataclass
class FileSummary:
    """Aggregated metadata produced after analysing a file."""

    file_id: str
    filename: str
    checksum: str
    file_size: int
    content_type: Optional[str]
    line_count: int
    error_count: int
    warning_count: int
    critical_count: int
    info_count: int
    sample_head: List[str]
    sample_tail: List[str]
    top_keywords: List[str]
    chunk_count: int = 0


class JobProcessor:
    """Async handlers for background job types leveraging embeddings + LLMs."""

    def __init__(self, job_service: Optional[JobService] = None) -> None:
        self._job_service = job_service or JobService()
        self._session_factory = get_db_session()
        self._embedding_service: Optional[EmbeddingService] = None
        self._embedding_lock = asyncio.Lock()

    async def close(self) -> None:
        """Release underlying resources."""
        if self._embedding_service is not None:
            try:
                await self._embedding_service.close()
            finally:
                self._embedding_service = None

    async def process_rca_analysis(self, job: Job) -> Dict[str, Any]:
        """Run the full RCA pipeline for the supplied job."""
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "ingestion", "status": "started"},
        )

        files = await self._list_job_files(str(job.id))
        if not files:
            raise ValueError("No files uploaded for analysis")

        file_summaries: List[FileSummary] = []
        total_chunks = 0

        for descriptor in files:
            summary = await self._process_single_file(job, descriptor)
            file_summaries.append(summary)
            total_chunks += summary.chunk_count

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "ingestion",
                "status": "completed",
                "files": len(file_summaries),
                "chunks": total_chunks,
            },
        )

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "status": "started"},
        )
        llm_output = await self._run_llm_analysis(job, file_summaries, "rca_analysis")
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "status": "completed"},
        )

        aggregate_metrics = {
            "files": len(file_summaries),
            "lines": sum(summary.line_count for summary in file_summaries),
            "errors": sum(summary.error_count for summary in file_summaries),
            "warnings": sum(summary.warning_count for summary in file_summaries),
            "critical": sum(summary.critical_count for summary in file_summaries),
            "chunks": total_chunks,
        }

        return {
            "job_id": str(job.id),
            "analysis_type": "rca_analysis",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "metrics": aggregate_metrics,
            "files": [asdict(summary) for summary in file_summaries],
            "llm": llm_output,
        }

    async def process_log_analysis(self, job: Job) -> Dict[str, Any]:
        """Alias for log-specific analysis (shares pipeline with RCA)."""
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "ingestion", "mode": "log-analysis", "status": "started"},
        )

        files = await self._list_job_files(str(job.id))
        if not files:
            raise ValueError("No files uploaded for analysis")

        file_summaries: List[FileSummary] = []
        total_chunks = 0

        for descriptor in files:
            summary = await self._process_single_file(job, descriptor)
            file_summaries.append(summary)
            total_chunks += summary.chunk_count

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "ingestion",
                "mode": "log-analysis",
                "status": "completed",
                "files": len(file_summaries),
                "chunks": total_chunks,
            },
        )

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "mode": "log-analysis", "status": "started"},
        )
        llm_output = await self._run_llm_analysis(job, file_summaries, "log_analysis")
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "llm", "mode": "log-analysis", "status": "completed"},
        )

        aggregate_metrics = {
            "files": len(file_summaries),
            "lines": sum(summary.line_count for summary in file_summaries),
            "errors": sum(summary.error_count for summary in file_summaries),
            "warnings": sum(summary.warning_count for summary in file_summaries),
            "critical": sum(summary.critical_count for summary in file_summaries),
            "chunks": total_chunks,
        }

        suspected_error_logs = [
            summary.filename
            for summary in file_summaries
            if summary.error_count or summary.critical_count
        ]

        return {
            "job_id": str(job.id),
            "analysis_type": "log_analysis",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "metrics": aggregate_metrics,
            "files": [asdict(summary) for summary in file_summaries],
            "suspected_error_logs": suspected_error_logs,
            "llm": llm_output,
        }

    async def process_embedding_generation(self, job: Job) -> Dict[str, Any]:
        """
        Generate embeddings for pre-existing documents linked to the job.
        Intended for reprocessing flows where text content already lives in the
        ``documents`` table.
        """
        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {"phase": "embedding-refresh", "status": "started"},
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(Document).where(Document.job_id == job.id).order_by(Document.chunk_index.asc())
            )
            documents = result.scalars().all()

        if not documents:
            raise ValueError("No documents available to embed")

        texts = [doc.content for doc in documents]
        embeddings = await self._generate_embeddings(texts)

        async with self._session_factory() as session:
            for document, vector in zip(documents, embeddings):
                existing = await session.get(Document, document.id)
                if existing:
                    existing.content_embedding = vector
            await session.commit()
            await self._job_service.publish_session_events(session)

        await self._job_service.create_job_event(
            str(job.id),
            "analysis-phase",
            {
                "phase": "embedding-refresh",
                "status": "completed",
                "documents": len(documents),
            },
        )

        return {
            "job_id": str(job.id),
            "analysis_type": "embedding_generation",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "document_count": len(documents),
        }

    async def _process_single_file(
        self,
        job: Job,
        descriptor: FileDescriptor,
    ) -> FileSummary:
        async with self._session_factory() as session:
            file_record = await session.get(File, descriptor.id)
            if file_record is None:
                raise ValueError(f"File {descriptor.id} missing for job {job.id}")

            await self._job_service.create_job_event(
                str(job.id),
                "file-processing-started",
                {
                    "file_id": descriptor.id,
                    "filename": descriptor.name,
                    "size": descriptor.size_bytes,
                },
                session=session,
            )

            text = await self._read_text(descriptor.path)
            summary, chunk_count = await self._analyse_and_store(
                session, job, file_record, text
            )
            summary.chunk_count = chunk_count

            await self._job_service.create_job_event(
                str(job.id),
                "file-processing-completed",
                {
                    "file_id": descriptor.id,
                    "filename": descriptor.name,
                    "chunks": chunk_count,
                    "errors": summary.error_count,
                    "warnings": summary.warning_count,
                    "critical": summary.critical_count,
                },
                session=session,
            )

            await session.commit()
            await self._job_service.publish_session_events(session)
            return summary

    async def _analyse_and_store(
        self,
        session: AsyncSession,
        job: Job,
        file_record: File,
        text: str,
    ) -> Tuple[FileSummary, int]:
        lines = text.splitlines()
        summary = self._build_summary(file_record, lines)
        chunks = self._chunk_lines(lines)
        embeddings = await self._generate_embeddings(chunks)

        for index, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
            document = Document(
                job_id=job.id,
                file_id=file_record.id,
                content=chunk_text,
                content_type="text/plain",
                metadata={
                    "filename": file_record.original_filename,
                    "chunk_index": index,
                },
                chunk_index=index,
                chunk_size=len(chunk_text),
                content_embedding=vector,
            )
            session.add(document)

        metadata = file_record.metadata or {}
        metadata["analysis_summary"] = {
            "line_count": summary.line_count,
            "error_count": summary.error_count,
            "warning_count": summary.warning_count,
            "critical_count": summary.critical_count,
            "top_keywords": summary.top_keywords,
        }
        file_record.metadata = metadata
        file_record.processed = True
        file_record.processed_at = datetime.utcnow()
        await session.flush()
        return summary, len(chunks)

    async def _run_llm_analysis(
        self,
        job: Job,
        summaries: Sequence[FileSummary],
        mode: str,
    ) -> Dict[str, Any]:
        provider_name = (job.provider or settings.llm.DEFAULT_PROVIDER).lower()
        model_name = job.model or settings.llm.OLLAMA_MODEL
        provider = LLMProviderFactory.create_provider(provider_name, model=model_name)

        prompt_lines = [
            f"Job ID: {job.id}",
            f"Scenario: {mode}",
            "",
            "Provide a concise root cause assessment and remediation plan based on the following file summaries:",
        ]
        for summary in summaries:
            prompt_lines.append(
                f"- {summary.filename} "
                f"(lines={summary.line_count}, errors={summary.error_count}, "
                f"warnings={summary.warning_count}, critical={summary.critical_count}, "
                f"top_keywords={', '.join(summary.top_keywords[:5])})"
            )
        prompt_lines.append("")
        prompt_lines.append(
            "Focus on likely causes, impacted areas, and actionable remediation steps."
        )

        messages = [
            LLMMessage(
                role="system",
                content="You are an experienced Site Reliability Engineer performing incident triage.",
            ),
            LLMMessage(role="user", content="\n".join(prompt_lines)),
        ]

        try:
            await provider.initialize()
            response = await provider.generate(messages, temperature=0.2)
            return {
                "provider": response.provider,
                "model": response.model,
                "summary": response.content.strip(),
                "usage": response.usage,
            }
        except Exception as exc:  # pragma: no cover - provider failures
            logger.warning(
                "LLM analysis failed for job %s using provider %s: %s",
                job.id,
                provider_name,
                exc,
            )
            return {
                "provider": provider_name,
                "model": model_name,
                "summary": "Automated analysis unavailable; review file summaries for context.",
                "error": str(exc),
            }
        finally:
            try:
                await provider.close()
            except Exception:
                logger.debug("Failed to close LLM provider cleanly", exc_info=True)

    async def _list_job_files(self, job_id: str) -> List[FileDescriptor]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(File)
                .where(File.job_id == job_id)
                .order_by(File.created_at.asc())
            )
            rows = result.scalars().all()

        descriptors = [
            FileDescriptor(
                id=str(row.id),
                path=row.file_path,
                name=row.original_filename,
                checksum=row.checksum,
                content_type=row.content_type,
                metadata=row.metadata,
                size_bytes=row.file_size,
            )
            for row in rows
        ]
        return descriptors

    async def _read_text(self, path: str) -> str:
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                return await handle.read()
        except UnicodeDecodeError:
            async with aiofiles.open(
                path, "r", encoding="latin-1", errors="ignore"
            ) as handle:
                return await handle.read()

    def _build_summary(self, file_record: File, lines: Sequence[str]) -> FileSummary:
        lowered = [line.lower() for line in lines]
        error_count = sum("error" in line for line in lowered)
        warning_count = sum("warning" in line for line in lowered)
        critical_count = sum("critical" in line for line in lowered)
        info_count = sum("info" in line for line in lowered)

        keywords: Counter[str] = Counter()
        for line in lowered:
            keywords.update(re.findall(r"[a-z]{4,}", line))

        sample_head = list(lines[:5])
        sample_tail = list(lines[-5:]) if len(lines) > 5 else []

        return FileSummary(
            file_id=str(file_record.id),
            filename=file_record.original_filename,
            checksum=file_record.checksum,
            file_size=file_record.file_size,
            content_type=file_record.content_type,
            line_count=len(lines),
            error_count=error_count,
            warning_count=warning_count,
            critical_count=critical_count,
            info_count=info_count,
            sample_head=sample_head,
            sample_tail=sample_tail,
            top_keywords=[word for word, _ in keywords.most_common(10)],
        )

    def _chunk_lines(self, lines: Sequence[str], max_chars: int = 2000) -> List[str]:
        chunks: List[str] = []
        buffer: List[str] = []
        length = 0

        for line in lines:
            buffer.append(line)
            length += len(line) + 1  # include newline
            if length >= max_chars:
                chunks.append("\n".join(buffer))
                buffer.clear()
                length = 0

        if buffer:
            chunks.append("\n".join(buffer))

        if not chunks:
            chunks.append("")

        return chunks

    async def _generate_embeddings(
        self, texts: Sequence[str]
    ) -> List[List[float]]:
        if not texts:
            return []

        service = await self._ensure_embedding_service()
        return await service.embed_texts(list(texts))

    async def _ensure_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is not None:
            return self._embedding_service

        async with self._embedding_lock:
            if self._embedding_service is None:
                service = EmbeddingService()
                await service.initialize()
                self._embedding_service = service
        return self._embedding_service  # type: ignore[return-value]


__all__ = ["JobProcessor"]
