"""Metadata generation utilities for YouTube uploads."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from .json_utils import ensure_schema_version, extract_json
from .model_router import ModelRouter
from .run_logger import build_metrics, emit_run_log
from .storage_utils import save_json
from .supabase_client import supabase


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
  "pinned_comment_variants": ["...", "..."],
  "thumbnail_variants": [
    {{"label": "A", "text": "...", "visual_brief": "..."}},
    {{"label": "B", "text": "...", "visual_brief": "..."}}
  ],
  "community_post": "...",
  "community_post_variants": ["...", "..."],
  "estimated_runtime_sec": 0,
  "speech_rate_wpm": 0,
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
) -> Dict[str, Any]:
    prompt = build_metadata_prompt(plan_payload, script_payload)
    router = ModelRouter.from_env()
    metadata_payload = extract_json(router.generate_content(prompt))
    _inject_runtime_estimates(script_payload, metadata_payload)
    ensure_schema_version(metadata_payload, DEFAULT_SCHEMA_VERSION)
    return metadata_payload


def _inject_runtime_estimates(script_payload: Dict[str, Any], metadata_payload: Dict[str, Any]) -> None:
    script_text = str(script_payload.get("script", ""))
    words = len(script_text.split())
    speech_rate_wpm = 230
    if str(script_payload.get("mode")) == "shorts":
        speech_rate_wpm = 175
    estimated_runtime_sec = int((words / max(speech_rate_wpm, 1)) * 60)
    metadata_payload["speech_rate_wpm"] = metadata_payload.get("speech_rate_wpm", speech_rate_wpm)
    metadata_payload["estimated_runtime_sec"] = metadata_payload.get("estimated_runtime_sec", estimated_runtime_sec)
    if "pinned_comment_variants" not in metadata_payload:
        metadata_payload["pinned_comment_variants"] = [
            metadata_payload.get("pinned_comment", ""),
            f"{metadata_payload.get('pinned_comment', '')}\n\n👉 Watch next: [Next Video Link]",
        ]
    if "community_post_variants" not in metadata_payload:
        metadata_payload["community_post_variants"] = [
            metadata_payload.get("community_post", ""),
            f"{metadata_payload.get('community_post', '')}\n\n✅ Save this post and share it with one friend.",
        ]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_metadata_payload(payload: Dict[str, Any]) -> List[str]:
    errors = []
    required = [
        "title",
        "description",
        "tags",
        "chapters",
        "pinned_comment",
        "thumbnail_variants",
        "community_post",
        "pinned_comment_variants",
        "community_post_variants",
        "estimated_runtime_sec",
        "speech_rate_wpm",
        "schema_version",
    ]
    for key in required:
        if key not in payload:
            errors.append(f"Missing required key: {key}")
    if "title" in payload and len(payload["title"]) > 90:
        errors.append("Title exceeds 90 characters.")
    if "description" in payload and len(payload["description"]) > 4000:
        errors.append("Description exceeds 4000 characters.")
    if "tags" in payload and not (5 <= len(payload["tags"]) <= 15):
        errors.append("Tags must contain 5-15 items.")
    if "thumbnail_variants" in payload and len(payload["thumbnail_variants"]) < 2:
        errors.append("Provide at least two thumbnail variants.")
    if "pinned_comment_variants" in payload and len(payload["pinned_comment_variants"]) < 2:
        errors.append("Provide at least two pinned comment variants.")
    if "community_post_variants" in payload and len(payload["community_post_variants"]) < 2:
        errors.append("Provide at least two community post variants.")
    return errors


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m lib.metadata_generator <plan_json> <script_json>",
            file=sys.stderr,
        )
        return 1

    plan_path = Path(sys.argv[1])
    script_path = Path(sys.argv[2])
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY in environment.", file=sys.stderr)
        return 1

    plan_payload = _load_json(plan_path)
    script_payload = _load_json(script_path)
    video_id = script_payload.get("video_id")
    if not video_id:
        print("Missing video_id in script payload.", file=sys.stderr)
        return 1

    try:
        metadata_payload = generate_metadata(
            plan_payload=plan_payload,
            script_payload=script_payload,
        )
        errors = _validate_metadata_payload(metadata_payload)
        if errors:
            raise ValueError("; ".join(errors))

        save_json("metadata", video_id, metadata_payload)
        supabase.table("video_metadata").upsert(
            {
                "video_id": video_id,
                "title": metadata_payload.get("title"),
                "description": metadata_payload.get("description"),
                "tags": metadata_payload.get("tags"),
                "chapters": metadata_payload.get("chapters"),
                "pinned_comment": metadata_payload.get("pinned_comment"),
                "thumbnail_variants": metadata_payload.get("thumbnail_variants"),
                "community_post": metadata_payload.get("community_post"),
                "pinned_comment_variants": metadata_payload.get("pinned_comment_variants"),
                "community_post_variants": metadata_payload.get("community_post_variants"),
                "estimated_runtime_sec": metadata_payload.get("estimated_runtime_sec"),
                "speech_rate_wpm": metadata_payload.get("speech_rate_wpm"),
                "schema_version": metadata_payload.get("schema_version"),
            },
            on_conflict="video_id",
        ).execute()
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
