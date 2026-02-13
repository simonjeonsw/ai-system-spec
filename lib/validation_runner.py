"""Run schema validation against planner/research/scene/script/image/motion JSON outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_json_file, validate_payload
from .storage_utils import normalize_video_id


VALIDATION_TARGETS = {
    "plan": "planner_output",
    "research": "research_output",
    "scenes": "scene_output",
    "image": "image_output",
    "motion": "motion_output",
    "script": "script_output",
}

STAGE_FILENAMES = {
    "research": "{video_id}_research.json",
    "plan": "{video_id}_plan.json",
    "scenes": "{video_id}_scenes.json",
    "image": "{video_id}_image.json",
    "motion": "{video_id}_motion.json",
    "script": "{video_id}_script.json",
}


def validate_files(stage: str, json_paths: Iterable[str]) -> None:
    schema_name = VALIDATION_TARGETS[stage]
    for path in json_paths:
        if stage == "scenes":
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            scenes = payload.get("scenes", [])
            if not scenes:
                raise ValueError("Scene output missing 'scenes' array.")
            for scene in scenes:
                validate_payload(schema_name, scene)
        elif stage == "image":
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            images = payload.get("images", [])
            if not images:
                raise ValueError("Image output missing 'images' array.")
            for image in images:
                validate_payload(schema_name, image)
        elif stage == "motion":
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            motions = payload.get("motions", [])
            if not motions:
                raise ValueError("Motion output missing 'motions' array.")
            for motion in motions:
                validate_payload(schema_name, motion)
        else:
            validate_json_file(schema_name, path)


def validate_all(video_id: str) -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    for stage, template in STAGE_FILENAMES.items():
        path = data_dir / template.format(video_id=video_id)
        if not path.exists():
            raise FileNotFoundError(f"Missing file for stage {stage}: {path}")
        validate_files(stage, [str(path)])


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m lib.validation_runner <plan|research|scenes|image|motion|script|all> <json_path>...",
            file=sys.stderr,
        )
        return 1

    stage = sys.argv[1].strip().lower()
    if stage == "all":
        if len(sys.argv) < 4 or sys.argv[2] != "--url":
            print(
                "Usage: python -m lib.validation_runner all --url <youtube_url_or_id>",
                file=sys.stderr,
            )
            return 1
        video_id = normalize_video_id(sys.argv[3])
        json_paths = []
    elif stage not in VALIDATION_TARGETS:
        print(f"Unknown stage: {stage}", file=sys.stderr)
        return 1
    else:
        json_paths = [str(Path(path)) for path in sys.argv[2:]]

    try:
        if stage == "all":
            validate_all(video_id)
        else:
            validate_files(stage, json_paths)
        emit_run_log(
            stage="validation",
            status="success",
            input_refs={"stage": stage, "files": json_paths or ["data/*"]},
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
