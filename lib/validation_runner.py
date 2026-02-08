"""Run schema validation against planner/research/scene/script JSON outputs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_json_file


VALIDATION_TARGETS = {
    "planner": "planner_output",
    "research": "research_output",
    "scene": "scene_output",
    "script": "script_output",
}


def validate_files(stage: str, json_paths: Iterable[str]) -> None:
    schema_name = VALIDATION_TARGETS[stage]
    for path in json_paths:
        validate_json_file(schema_name, path)


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m lib.validation_runner <planner|research|scene|script> <json_path>...",
            file=sys.stderr,
        )
        return 1

    stage = sys.argv[1].strip().lower()
    if stage not in VALIDATION_TARGETS:
        print(f"Unknown stage: {stage}", file=sys.stderr)
        return 1

    json_paths = [str(Path(path)) for path in sys.argv[2:]]
    try:
        validate_files(stage, json_paths)
        emit_run_log(
            stage="validation",
            status="success",
            input_refs={"stage": stage, "files": json_paths},
            metrics=build_metrics(cache_hit=False),
        )
        print("Validation passed.")
        return 0
    except Exception as exc:
        emit_run_log(
            stage="validation",
            status="failure",
            input_refs={"stage": stage, "files": json_paths},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
