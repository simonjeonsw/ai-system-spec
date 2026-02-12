"""Build structure-only scene contracts from legacy/raw scene payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


SceneContext = Dict[str, str]


def build_scene_contract(raw_scene_output: Dict[str, Any]) -> Tuple[Dict[str, Any], List[SceneContext]]:
    """Convert raw scene payload into structure-only scene contract.

    Returns:
        - scene_contract: payload aligned to scene_output schema intent
        - scene_contexts: auxiliary context for downstream image generation
    """
    scenes_in = list(raw_scene_output.get("scenes", []))
    scene_items: list[Dict[str, Any]] = []
    scene_contexts: list[SceneContext] = []
    cursor_sec = 0.0

    for idx, scene in enumerate(scenes_in, start=1):
        scene_id = str(scene.get("scene_id", f"s{idx:02d}"))
        narration = str(scene.get("narration_prompt", "")).strip()
        objective = str(scene.get("objective", "Deliver script segment with clear transition.")).strip()
        script_ref = narration[:140] if narration else f"script_segment_{idx:02d}"
        duration = max(6.0, min(24.0, round(max(12, len(narration.split()) // 2), 1)))
        start_sec = round(cursor_sec, 1)
        end_sec = round(cursor_sec + duration, 1)
        cursor_sec = end_sec

        scene_items.append(
            {
                "scene_id": scene_id,
                "objective": objective,
                "script_refs": [script_ref],
                "start_sec": start_sec,
                "end_sec": end_sec,
                "transition_note": str(scene.get("transition_note", "Advance to next scene.")).strip(),
                "schema_version": "2.0",
            }
        )

        scene_contexts.append(
            {
                "scene_id": scene_id,
                "objective": objective,
                "visual_cue": str(scene.get("visual_cue") or objective).strip(),
                "overlay_text": str(scene.get("overlay_text") or "").strip(),
                "style_profile": str(scene.get("style_profile") or raw_scene_output.get("style_profile") or "isometric_3d"),
            }
        )

    scene_contract = {
        "scenes": scene_items,
        "scene_engine_version": raw_scene_output.get("scene_engine_version", "2.0"),
        "source_script_hash": raw_scene_output.get("source_script_hash", ""),
    }
    return scene_contract, scene_contexts
