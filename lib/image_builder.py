"""Build static image contracts from structure scene contexts."""

from __future__ import annotations

from typing import Dict, List


def build_image_contract(scene_contexts: List[Dict[str, str]]) -> Dict[str, object]:
    images = []
    for context in scene_contexts:
        scene_id = context["scene_id"]
        images.append(
            {
                "scene_id": scene_id,
                "asset_id": f"{scene_id}-img",
                "composition": context.get("visual_cue", ""),
                "style_profile": context.get("style_profile", "isometric_3d"),
                "overlay_spec": context.get("overlay_text", ""),
                "schema_version": "1.0",
            }
        )
    return {"images": images, "schema_version": "1.0"}
