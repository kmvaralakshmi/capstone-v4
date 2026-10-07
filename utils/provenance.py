"""Shared provenance and timing helpers for auditable pipeline outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, Optional
from uuid import uuid4


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp with a timezone marker."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    """Create a unique identifier for one pipeline execution."""
    return f"run-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"


def metric_provenance(
    *,
    run_id: str,
    source: str,
    evidence_source: str,
    source_url: str = "",
    section: str = "",
    fallback_used: bool = False,
    discrepancy_status: str = "not_evaluated",
) -> Dict[str, Any]:
    """Build the common provenance fields for a metric record."""
    return {
        "Run_ID": run_id,
        "Source": source,
        "Evidence_Source": evidence_source,
        "Source_URL": source_url,
        "Retrieved_At": utc_timestamp(),
        "Section": section,
        "Fallback_Used": fallback_used,
        "Discrepancy_Status": discrepancy_status,
    }


class StageTimer:
    """Measure one pipeline stage and expose a serializable timing record."""

    def __init__(
        self,
        *,
        run_id: str,
        stage: str,
        source: str = "",
        fallback_used: bool = False,
    ) -> None:
        self.run_id = run_id
        self.stage = stage
        self.source = source
        self.fallback_used = fallback_used
        self.started_at = utc_timestamp()
        self._started = perf_counter()
        self.error: Optional[str] = None

    def finish(
        self,
        *,
        status: str = "success",
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Finish timing and return a consistent stage record."""
        self.error = error
        return {
            "Run_ID": self.run_id,
            "Stage": self.stage,
            "Source": self.source,
            "Stage_Status": status,
            "Start_Time": self.started_at,
            "End_Time": utc_timestamp(),
            "Duration_Seconds": round(perf_counter() - self._started, 3),
            "Error": error or "",
            "Fallback_Used": self.fallback_used,
        }
