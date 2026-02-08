"""End-to-end pipeline runner for research → metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .json_utils import extract_json
from .metadata_generator import generate_metadata
from .planner import ContentPlanner
from .researcher import VideoResearcher
from .scene_builder import SceneBuilder
from .scripter import ContentScripter
from .storage_utils import normalize_video_id, save_json
from .supabase_client import supabase
from .validation_runner import validate_all


def _parse_payload(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return extract_json(text)


def run_pipeline(video_input: str, refresh: bool = False) -> Dict[str, Any]:
    video_id = normalize_video_id(video_input)
    researcher = VideoResearcher()
    planner = ContentPlanner()
    scripter = ContentScripter()
    scene_builder = SceneBuilder()

    research_text = researcher.analyze_viral_strategy(video_id, force_update=refresh)
    research_payload = _parse_payload(research_text)

    plan_text = planner.create_project_plan(video_id)
    if plan_text.startswith("❌"):
        raise ValueError(plan_text)
    plan_payload = _parse_payload(plan_text)

    scene_output = scene_builder.build_scenes(research_payload)
    save_json("scene_builder", video_id, scene_output)
    supabase.table("video_scenes").upsert(
        {
            "video_id": video_id,
            "content": json.dumps(scene_output, ensure_ascii=False),
        },
        on_conflict="video_id",
    ).execute()

    script_text = scripter.write_full_script(video_id)
    if script_text.startswith("❌"):
        raise ValueError(script_text)
    script_payload = _parse_payload(script_text)
    script_payload["video_id"] = video_id
    supabase.table("scripts").insert(
        {"content": json.dumps(script_payload, ensure_ascii=False)}
    ).execute()
    save_json("script", video_id, script_payload)

    metadata_payload = generate_metadata(
        plan_payload=plan_payload,
        script_payload=script_payload,
    )
    save_json("metadata", video_id, metadata_payload)
    supabase.table("video_metadata").upsert(
        {
            "video_id": video_id,
            "title": metadata_payload.get("title"),
            "description": metadata_payload.get("description"),
            "tags": metadata_payload.get("tags"),
            "chapters": metadata_payload.get("chapters"),
            "pinned_comment": metadata_payload.get("pinned_comment"),
            "schema_version": metadata_payload.get("schema_version"),
        },
        on_conflict="video_id",
    ).execute()

    return {
        "video_id": video_id,
        "research": research_payload,
        "plan": plan_payload,
        "scenes": scene_output,
        "script": script_payload,
        "metadata": metadata_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full pipeline end-to-end.")
    parser.add_argument("--url", required=True, help="YouTube URL or video ID")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh (ignore cached data)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation_runner all --url after completion",
    )
    parser.add_argument(
        "--video-path",
        help="Optional path to video file to upload after metadata generation",
    )
    parser.add_argument(
        "--privacy-status",
        default="private",
        help="YouTube privacy status (private|unlisted|public)",
    )
    parser.add_argument(
        "--notify-subscribers",
        action="store_true",
        help="Notify subscribers on upload",
    )
    args = parser.parse_args()

    result = run_pipeline(args.url, refresh=args.refresh)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.validate:
        validate_all(normalize_video_id(args.url))

    if args.video_path:
        from .ops import publish_video

        metadata_path = Path(__file__).resolve().parent.parent / "data" / f"metadata_{result['video_id']}.json"
        payload = {
            "video_id": result["video_id"],
            "status": "published",
            "metadata_path": str(metadata_path),
            "video_path": args.video_path,
            "privacy_status": args.privacy_status,
            "notify_subscribers": args.notify_subscribers,
        }
        upload_result = publish_video(payload)
        print(json.dumps({"upload": upload_result}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
