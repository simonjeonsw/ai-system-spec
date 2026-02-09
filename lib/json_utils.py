"""JSON utility helpers for model output handling."""

from __future__ import annotations

import json
import re
from typing import Any, Dict


def extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from model output."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object detected in model output.")
    return json.loads(text[start : end + 1])


def extract_json_relaxed(text: str) -> Dict[str, Any]:
    """Attempt to recover JSON from partially corrupted model output."""
    try:
        return extract_json(text)
    except Exception:
        start = text.find("{")
        if start == -1:
            raise
        candidate = text[start:]
        if "}" in candidate:
            candidate = candidate[: candidate.rfind("}") + 1]
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")
        if close_braces < open_braces:
            candidate += "}" * (open_braces - close_braces)
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        return json.loads(candidate)


def recover_script_payload(text: str) -> Dict[str, Any]:
    """Fallback parser to recover script payload when JSON is malformed."""
    try:
        return extract_json_relaxed(text)
    except Exception:
        script_match = re.search(
            r'"script"\s*:\s*"(?P<script>.*?)"\s*(?:,|})',
            text,
            re.DOTALL,
        )
        if not script_match:
            script_match = re.search(
                r'"script_long"\s*:\s*"(?P<script>.*?)"\s*(?:,|})',
                text,
                re.DOTALL,
            )
        if not script_match:
            script_match = re.search(
                r'"script_shorts"\s*:\s*"(?P<script>.*?)"\s*(?:,|})',
                text,
                re.DOTALL,
            )
        citations_match = re.search(
            r'"citations"\s*:\s*\[(?P<citations>.*?)\]',
            text,
            re.DOTALL,
        )
        script_text = script_match.group("script") if script_match else text
        script_text = script_text.replace('\\"', '"').replace("\\n", "\n")
        citations = []
        if citations_match:
            raw = citations_match.group("citations")
            citations = [item.strip().strip('"') for item in raw.split(",") if item.strip()]
        return {"script": script_text, "citations": citations, "schema_version": "1.0"}


def ensure_schema_version(payload: Dict[str, Any], version: str) -> Dict[str, Any]:
    if payload.get("schema_version"):
        return payload
    payload["schema_version"] = version
    return payload
