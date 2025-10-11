"""
Lightweight job processor implementations.

These routines provide the first functional pass at the RCA / log-analysis
pipelines so that the worker can return meaningful data while the richer
ML-based implementation is being built.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from core.db.models import Job


class JobProcessor:
    """Async handlers for the supported background job types."""

    async def process_rca_analysis(self, job: Job) -> Dict[str, Any]:
        """
        Produce a skeleton RCA report using the available manifest metadata.

        The intent is to keep the pipeline moving while the full LLM/embedding
        stack is wired up. The structure mirrors the future shape so that API
        consumers can already integrate.
        """
        manifest = job.input_manifest or {}
        files = self._normalise_files(manifest)

        return {
            "job_id": str(job.id),
            "analysis_type": "rca_analysis",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": self._summarise_files(files),
            "files": files,
            "observations": manifest.get("observations", []),
            "notes": [
                "This is a placeholder RCA report. LLM-driven insights will be added in a later iteration."
            ],
        }

    async def process_log_analysis(self, job: Job) -> Dict[str, Any]:
        """
        Perform a lightweight log analysis by classifying files and surfacing
        a couple of starter metrics.
        """
        manifest = job.input_manifest or {}
        files = self._normalise_files(manifest)

        error_like = [
            f for f in files if "error" in f.get("name", "").lower()
        ]

        return {
            "job_id": str(job.id),
            "analysis_type": "log_analysis",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": self._summarise_files(files),
            "total_files": len(files),
            "suspected_error_logs": [f.get("name") for f in error_like],
            "notes": [
                "Automated pattern detection is not yet enabled.",
                "Use this report to validate ingestion while deeper analytics are implemented.",
            ],
        }

    async def process_embedding_generation(self, job: Job) -> Dict[str, Any]:
        """
        Stub embedding generation – returns deterministic mock vectors for the
        supplied documents so downstream code can be exercised.
        """
        manifest = job.input_manifest or {}
        documents = manifest.get("documents") or manifest.get("files") or []

        embeddings = [
            {
                "document": doc if isinstance(doc, str) else doc.get("name"),
                "vector": self._mock_vector(index),
            }
            for index, doc in enumerate(documents)
        ]

        return {
            "job_id": str(job.id),
            "analysis_type": "embedding_generation",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "embeddings": embeddings,
            "notes": [
                "Mock embeddings generated for integration testing purposes.",
                "Replace with the real embedding service once configured.",
            ],
        }

    @staticmethod
    def _normalise_files(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ensure file manifests are represented as dictionaries."""
        files = manifest.get("files", [])
        normalised: List[Dict[str, Any]] = []

        for item in files:
            if isinstance(item, dict):
                normalised.append(
                    {
                        "name": item.get("name") or item.get("filename"),
                        "size": item.get("size"),
                        "content_type": item.get("content_type"),
                    }
                )
            else:
                normalised.append({"name": str(item), "size": None, "content_type": None})

        return normalised

    @staticmethod
    def _summarise_files(files: List[Dict[str, Any]]) -> str:
        if not files:
            return "No files supplied for analysis."

        named = [f.get("name") for f in files if f.get("name")]
        return f"Prepared {len(files)} file(s) for analysis: {', '.join(named[:5])}"

    @staticmethod
    def _mock_vector(seed: int) -> List[float]:
        """Generate a deterministic pseudo vector for predictable tests."""
        # Keep it tiny to minimise payload size while exercising consumers.
        base = float(seed + 1)
        return [base, base / 2.0, base / 3.0]


__all__ = ["JobProcessor"]
