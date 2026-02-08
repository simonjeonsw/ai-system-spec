"""JSON utility helpers for model output handling."""

from __future__ import annotations

import json
from typing import Any, Dict


def extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from model output."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object detected in model output.")
    return json.loads(text[start : end + 1])


def ensure_schema_version(payload: Dict[str, Any], version: str) -> Dict[str, Any]:
    if payload.get("schema_version"):
        return payload
    payload["schema_version"] = version
    return payload
