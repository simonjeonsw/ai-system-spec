"""End-to-end pipeline runner for research → metadata."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .json_utils import extract_json
from .metadata_generator import generate_metadata
from .planner import ContentPlanner
from .researcher import VideoResearcher
from .scene_builder import SceneBuilder
from .scripter import ContentScripter
from .run_logger import build_metrics, emit_run_log
from .storage_utils import normalize_video_id, save_json
from .supabase_client import supabase
from .validation_runner import validate_all
from .validator import ScriptValidator


def _parse_payload(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return extract_json(text)

def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("429", "5xx", "timeout", "resource_exhausted"))

def _log_run_id(root_run_id: str, stage: str, attempt: int) -> str:
    return f"{root_run_id}:{stage}:{attempt}"


def _run_stage(
    *,
    stage: str,
    run_id: str,
    input_refs: Dict[str, Any],
    action: Callable[[], Any],
    max_retries: int = 3,
    base_delay_s: float = 1.0,
) -> Tuple[Any, int]:
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        start_time = time.monotonic()
        try:
            result = action()
            latency_ms = int((time.monotonic() - start_time) * 1000)
            emit_run_log(
                stage=stage,
                status="success",
                input_refs={**input_refs, "root_run_id": run_id},
                output_refs={"status": "completed"},
                metrics=build_metrics(
                    latency_ms=latency_ms,
                    cache_hit=False,
                    retry_count=attempt - 1,
                ),
                attempts=attempt,
                run_id=_log_run_id(run_id, stage, attempt),
            )
            return result, attempt
        except Exception as exc:
            last_error = exc
            latency_ms = int((time.monotonic() - start_time) * 1000)
            emit_run_log(
                stage=stage,
                status="failure",
                input_refs={**input_refs, "root_run_id": run_id},
                error_summary=str(exc),
                metrics=build_metrics(
                    latency_ms=latency_ms,
                    cache_hit=False,
                    retry_count=attempt - 1,
                ),
                attempts=attempt,
                run_id=_log_run_id(run_id, stage, attempt),
            )
            if not _is_transient_error(exc) or attempt >= max_retries:
                break
            time.sleep(base_delay_s * (2 ** (attempt - 1)))
    raise RuntimeError(f"{stage} failed after {max_retries} attempts") from last_error


def run_pipeline(video_input: str, refresh: bool = False) -> Dict[str, Any]:
    video_id = normalize_video_id(video_input)
    researcher = VideoResearcher()
    planner = ContentPlanner()
    scripter = ContentScripter()
    scene_builder = SceneBuilder()
    run_id = emit_run_log(
        stage="orchestrator",
        status="success",
        input_refs={"video_id": video_id},
        output_refs={"status": "started"},
        metrics=build_metrics(cache_hit=False),
    )

    verification_report = None
    try:
        research_text, _ = _run_stage(
            stage="research",
            run_id=run_id,
            input_refs={"video_id": video_id, "refresh": refresh},
            action=lambda: researcher.analyze_viral_strategy(video_id, force_update=refresh),
        )
        research_payload = _parse_payload(research_text)

        plan_text, _ = _run_stage(
            stage="planner",
            run_id=run_id,
            input_refs={"video_id": video_id},
            action=lambda: planner.create_project_plan(video_id),
        )
        if plan_text.startswith("❌"):
            raise ValueError(plan_text)
        plan_payload = _parse_payload(plan_text)

        scene_output, _ = _run_stage(
            stage="scene_builder",
            run_id=run_id,
            input_refs={"video_id": video_id},
            action=lambda: scene_builder.build_scenes(research_payload),
        )
        save_json("scene_builder", video_id, scene_output)
        supabase.table("video_scenes").upsert(
            {
                "video_id": video_id,
                "content": json.dumps(scene_output, ensure_ascii=False),
            },
            on_conflict="video_id",
        ).execute()

        source_ids = [source.get("source_id") for source in research_payload.get("sources", []) if source.get("source_id")]
        script_text, _ = _run_stage(
            stage="script",
            run_id=run_id,
            input_refs={"video_id": video_id},
            action=lambda: scripter.write_full_script(
                video_id,
                source_ids=source_ids,
                mode="long",
            ),
        )
        if script_text.startswith("❌"):
            raise ValueError(script_text)
        script_payload = _parse_payload(script_text)
        script_payload["video_id"] = video_id
        script_payload["mode"] = "long"
        supabase.table("scripts").insert(
            {"content": json.dumps(script_payload, ensure_ascii=False)}
        ).execute()
        save_json("script_long", video_id, script_payload)

        shorts_text, _ = _run_stage(
            stage="script_shorts",
            run_id=run_id,
            input_refs={"video_id": video_id},
            action=lambda: scripter.write_full_script(
                video_id,
                source_ids=source_ids,
                mode="shorts",
            ),
        )
        if shorts_text.startswith("❌"):
            raise ValueError(shorts_text)
        shorts_payload = _parse_payload(shorts_text)
        shorts_payload["video_id"] = video_id
        shorts_payload["mode"] = "shorts"
        supabase.table("scripts").insert(
            {"content": json.dumps(shorts_payload, ensure_ascii=False)}
        ).execute()
        save_json("script_shorts", video_id, shorts_payload)

        validator = ScriptValidator(research_payload, script_payload)
        verification_result = validator.validate()
        verification_report = {
            "status": verification_result.status,
            "errors": verification_result.errors,
            "sentence_map": verification_result.sentence_map,
        }
        emit_run_log(
            stage="validator",
            status="success" if verification_result.status == "pass" else "failure",
            input_refs={"video_id": video_id, "root_run_id": run_id},
            output_refs={"verification_report": verification_report},
            metrics=build_metrics(cache_hit=False),
            run_id=_log_run_id(run_id, "validator", 1),
        )

        if verification_result.status != "pass":
            feedback = "; ".join(verification_result.errors)
            script_text, _ = _run_stage(
                stage="script_repair",
                run_id=run_id,
                input_refs={"video_id": video_id, "retry": "validator_feedback"},
                action=lambda: scripter.write_full_script_with_feedback(
                    video_id,
                    feedback,
                    source_ids=source_ids,
                    mode="long",
                ),
            )
            if script_text.startswith("❌"):
                raise ValueError(script_text)
            script_payload = _parse_payload(script_text)
            script_payload["video_id"] = video_id
            script_payload["mode"] = "long"
            supabase.table("scripts").insert(
                {"content": json.dumps(script_payload, ensure_ascii=False)}
            ).execute()
            save_json("script_long", video_id, script_payload)

            validator = ScriptValidator(research_payload, script_payload)
            verification_result = validator.validate()
            verification_report = {
                "status": verification_result.status,
                "errors": verification_result.errors,
                "sentence_map": verification_result.sentence_map,
            }
            emit_run_log(
                stage="validator",
                status="success" if verification_result.status == "pass" else "failure",
                input_refs={
                    "video_id": video_id,
                    "retry": "validator_feedback",
                    "root_run_id": run_id,
                },
                output_refs={"verification_report": verification_report},
                metrics=build_metrics(cache_hit=False),
                run_id=_log_run_id(run_id, "validator", 2),
            )
            if verification_result.status != "pass":
                emit_run_log(
                    stage="validator",
                    status="warning",
                    input_refs={"video_id": video_id, "root_run_id": run_id},
                    output_refs={"note": "validation failed after auto-repair; proceeding"},
                    metrics=build_metrics(cache_hit=False),
                    run_id=_log_run_id(run_id, "validator", 3),
                )

        metadata_payload, _ = _run_stage(
            stage="metadata",
            run_id=run_id,
            input_refs={"video_id": video_id},
            action=lambda: generate_metadata(
                plan_payload=plan_payload,
                script_payload=script_payload,
            ),
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
    except Exception as exc:
        failure_payload = {
            "video_id": video_id,
            "status": "failed",
        }
        try:
            supabase.table("video_uploads").upsert(
                {
                    **failure_payload,
                    "metadata_path": None,
                    "video_path": None,
                },
                on_conflict="video_id",
            ).execute()
        except Exception as insert_exc:
            if "metadata_path" in str(insert_exc):
                supabase.table("video_uploads").upsert(
                    failure_payload,
                    on_conflict="video_id",
                ).execute()
            else:
                raise
        raise exc

    return {
        "run_id": run_id,
        "video_id": video_id,
        "research": research_payload,
        "plan": plan_payload,
        "scenes": scene_output,
        "script_long": script_payload,
        "script_shorts": shorts_payload,
        "verification_report": verification_report,
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
    manifest_path = Path(__file__).resolve().parent.parent / "data" / f"pipeline_{result['video_id']}.json"
    manifest = {
        "video_id": result["video_id"],
        "files": {
            "research": f"data/research_{result['video_id']}.json",
            "planner": f"data/planner_{result['video_id']}.json",
            "scene_builder": f"data/scene_builder_{result['video_id']}.json",
            "script": f"data/script_{result['video_id']}.json",
            "metadata": f"data/metadata_{result['video_id']}.json",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

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
