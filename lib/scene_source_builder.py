"""Scene source builder that emits canonical structure-only scene contracts."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    cleaned = re.sub(r"^[\s:;,\.\-–—]+", "", cleaned)
    return cleaned


def _sentence(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return "Deliver next script beat with clear continuity."
    if normalized[-1] not in ".?!":
        normalized += "."
    return normalized


def build_structure_only_scenes(visual_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    scenes: list[Dict[str, Any]] = []
    cursor_sec = 0.0
    for index, block in enumerate(visual_blocks, start=1):
        narration = _sentence(str(block.get("narration", "")))
        objective = narration[:180]
        duration = max(6.0, min(24.0, round(max(12, len(narration.split()) // 2), 1)))
        start_sec = round(cursor_sec, 1)
        end_sec = round(cursor_sec + duration, 1)
        cursor_sec = end_sec

        scenes.append(
            {
                "scene_id": f"s{index:02d}",
                "objective": objective,
                "script_refs": [narration[:140]],
                "start_sec": start_sec,
                "end_sec": end_sec,
                "transition_note": "Advance to the next semantic beat while preserving narrative continuity.",
                "schema_version": "2.0",
            }
        )

    return {"scenes": scenes}
