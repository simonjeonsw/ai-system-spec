"""Ops stage utilities for publishing and metadata experiment logging."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .run_logger import build_metrics, emit_run_log
from .supabase_client import supabase


def log_experiment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a metadata experiment record and return the stored payload."""
    required_keys = {"video_id", "experiment_type", "start_date"}
    missing = required_keys - set(payload.keys())
    if missing:
        raise ValueError(f"Missing required experiment fields: {sorted(missing)}")

    experiment_payload = {
        "video_id": payload["video_id"],
        "experiment_type": payload["experiment_type"],
        "title_variant": payload.get("title_variant"),
        "thumbnail_variant": payload.get("thumbnail_variant"),
        "start_date": payload.get("start_date") or datetime.now(timezone.utc).isoformat(),
        "end_date": payload.get("end_date"),
        "ctr": payload.get("ctr"),
        "avd": payload.get("avd"),
        "notes": payload.get("notes"),
    }

    supabase.table("metadata_experiments").insert(experiment_payload).execute()
    return experiment_payload


def publish_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a video via YouTube API when metadata/video paths are provided."""
    required_keys = {"video_id", "status"}
    missing = required_keys - set(payload.keys())
    if missing:
        raise ValueError(f"Missing required publish fields: {sorted(missing)}")

    result: Dict[str, Any] = {
        "video_id": payload["video_id"],
        "status": payload["status"],
        "published_at": payload.get("published_at") or datetime.now(timezone.utc).isoformat(),
        "notes": payload.get("notes"),
    }

    if payload.get("video_path") and payload.get("metadata_path"):
        from .youtube_uploader import upload_video

        upload_result = upload_video(
            metadata=json.loads(Path(payload["metadata_path"]).read_text(encoding="utf-8")),
            video_path=Path(payload["video_path"]),
            privacy_status=payload.get("privacy_status", "private"),
            notify_subscribers=payload.get("notify_subscribers", False),
        )
        result.update(upload_result)
        upload_payload = {
            "video_id": upload_result.get("video_id") or payload["video_id"],
            "status": upload_result.get("status"),
            "notify_subscribers": upload_result.get("notify_subscribers"),
            "published_at": result.get("published_at"),
            "metadata_path": payload.get("metadata_path"),
            "video_path": payload.get("video_path"),
        }
        try:
            supabase.table("video_uploads").upsert(
                upload_payload,
                on_conflict="video_id",
            ).execute()
        except Exception as insert_exc:
            if "metadata_path" in str(insert_exc):
                supabase.table("video_uploads").upsert(
                    {
                        "video_id": upload_payload["video_id"],
                        "status": upload_payload["status"],
                        "notify_subscribers": upload_payload["notify_subscribers"],
                        "published_at": upload_payload["published_at"],
                        "video_path": upload_payload["video_path"],
                    },
                    on_conflict="video_id",
                ).execute()
            else:
                raise

    emit_run_log(
        stage="ops",
        status="success" if payload["status"] == "published" else "failure",
        input_refs={"video_id": payload["video_id"]},
        output_refs=result,
        metrics=build_metrics(cache_hit=False),
    )
    return result


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m lib.ops <publish|log_experiment> <json_path>",
            file=sys.stderr,
        )
        return 1

    mode = sys.argv[1].strip().lower()
    json_path = Path(sys.argv[2])
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    try:
        if mode == "publish":
            result = publish_video(payload)
        elif mode == "log_experiment":
            result = log_experiment(payload)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="ops",
            status="failure",
            input_refs={"mode": mode, "json_path": str(json_path)},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Ops stage failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
