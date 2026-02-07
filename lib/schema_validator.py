"""Schema validation helpers for planner/research/scene/script outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "spec" / "schemas"


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
