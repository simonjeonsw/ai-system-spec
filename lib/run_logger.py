"""Run-log utilities for pipeline observability."""

from __future__ import annotations

import sys
import uuid
from typing import Any, Dict, Optional

from .supabase_client import supabase


def emit_run_log(
    *,
    stage: str,
    status: str,
    input_refs: Optional[Dict[str, Any]] = None,
    output_refs: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    error_summary: Optional[str] = None,
    attempts: int = 0,
    run_id: Optional[str] = None,
) -> str:
    """Insert a pipeline_runs record and return the run_id."""
    run_id = run_id or str(uuid.uuid4())
    payload = {
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "attempts": attempts,
        "input_refs": input_refs or {},
        "output_refs": output_refs or {},
        "error_summary": error_summary,
        "metrics": metrics or {},
    }
    try:
        supabase.table("pipeline_runs").insert(payload).execute()
    except Exception as exc:  # Avoid crashing on logging failures.
        print(f"Run log insert failed: {exc}", file=sys.stderr)
    return run_id
