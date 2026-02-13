"""Schema validation helpers for planner/research/scene/script/image/motion outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "spec" / "schemas"

_FORBIDDEN_FIELDS_BY_SCHEMA = {
    # Scene must remain structure/timing only.
    "scene_output": {
        "visual_prompt",
        "camera_angle",
        "overlay_text",
        "style_profile",
        "visual_style",
        "animation",
        "easing",
        "transition_fx",
        "asset_id",
        "entrance",
        "exit",
        "emphasis",
        "timeline",
    },
    # Image is static composition only.
    "image_output": {
        "entrance",
        "exit",
        "emphasis",
        "timeline",
        "scene_order",
        "duration_reallocation",
    },
    # Motion is temporal directives only.
    "motion_output": {
        "scene_order",
        "duration_reallocation",
        "script",
        "script_text",
        "narration",
        "overlay_spec",
        "composition",
        "style_profile",
    },
}


def load_schema(name: str) -> Dict[str, Any]:
    schema_path = SCHEMA_DIR / f"{name}.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_payload(schema_name: str, payload: Dict[str, Any]) -> None:
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        messages = "\n".join(f"- {error.message}" for error in errors)
        raise ValueError(f"Schema validation failed:\n{messages}")

    forbidden_fields = _FORBIDDEN_FIELDS_BY_SCHEMA.get(schema_name, set())
    if forbidden_fields:
        collided = sorted(field for field in payload.keys() if field in forbidden_fields)
        if collided:
            raise ValueError(
                f"Contract boundary validation failed for {schema_name}: "
                f"forbidden fields present: {', '.join(collided)}"
            )


def validate_json_file(schema_name: str, json_path: str) -> None:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    validate_payload(schema_name, payload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate JSON against a schema.")
    parser.add_argument("schema", help="Schema name (e.g., planner_output)")
    parser.add_argument("json_path", help="Path to JSON file")
    args = parser.parse_args()

    validate_json_file(args.schema, args.json_path)
    print("Schema validation passed.")
