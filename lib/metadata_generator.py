"""Metadata generation utilities for YouTube uploads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from google.genai import Client

from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log


DEFAULT_SCHEMA_VERSION = "1.0"


def build_metadata_prompt(plan_payload: Dict[str, Any], script_payload: Dict[str, Any]) -> str:
    return f"""
You are a YouTube metadata generator. Return JSON only with this schema:
{{
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "chapters": [{{"timecode": "00:00", "title": "..."}}],
  "pinned_comment": "...",
  "schema_version": "{DEFAULT_SCHEMA_VERSION}"
}}

Constraints:
- Output English only.
- Title max 90 characters.
- Description max 4000 characters.
- Tags: 5-15 items.
- Chapters should be ordered and cover major beats.

Planner JSON:
{json.dumps(plan_payload, ensure_ascii=False)}

Script JSON:
{json.dumps(script_payload, ensure_ascii=False)}
"""


def generate_metadata(
    *,
    plan_payload: Dict[str, Any],
    script_payload: Dict[str, Any],
    api_key: str,
    model_id: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    client = Client(api_key=api_key)
    prompt = build_metadata_prompt(plan_payload, script_payload)
    response = client.models.generate_content(model=model_id, contents=prompt)
    metadata_payload = extract_json(response.text)
    ensure_schema_version(metadata_payload, DEFAULT_SCHEMA_VERSION)
    return metadata_payload


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_metadata_payload(payload: Dict[str, Any]) -> List[str]:
    errors = []
    required = ["title", "description", "tags", "chapters", "pinned_comment", "schema_version"]
    for key in required:
        if key not in payload:
            errors.append(f"Missing required key: {key}")
    if "title" in payload and len(payload["title"]) > 90:
        errors.append("Title exceeds 90 characters.")
    if "description" in payload and len(payload["description"]) > 4000:
        errors.append("Description exceeds 4000 characters.")
    if "tags" in payload and not (5 <= len(payload["tags"]) <= 15):
        errors.append("Tags must contain 5-15 items.")
    return errors


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: python -m lib.metadata_generator <plan_json> <script_json> <api_key>",
            file=sys.stderr,
        )
        return 1

    plan_path = Path(sys.argv[1])
    script_path = Path(sys.argv[2])
    api_key = sys.argv[3]

    plan_payload = _load_json(plan_path)
    script_payload = _load_json(script_path)

    try:
        metadata_payload = generate_metadata(
            plan_payload=plan_payload,
            script_payload=script_payload,
            api_key=api_key,
        )
        errors = _validate_metadata_payload(metadata_payload)
        if errors:
            raise ValueError("; ".join(errors))

        emit_run_log(
            stage="metadata",
            status="success",
            input_refs={"plan": str(plan_path), "script": str(script_path)},
            output_refs={"metadata": "generated"},
            metrics=build_metrics(cache_hit=False),
        )
        print(json.dumps(metadata_payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="metadata",
            status="failure",
            input_refs={"plan": str(plan_path), "script": str(script_path)},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Metadata generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
