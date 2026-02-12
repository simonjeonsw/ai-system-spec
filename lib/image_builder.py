"""Build static image contracts from canonical structure-only scene contracts."""

from __future__ import annotations

from typing import Any, Dict


def _derive_overlay_from_ref(script_ref: str) -> str:
    tokens = [tok for tok in script_ref.split() if any(ch.isdigit() for ch in tok)]
    return tokens[0][:24] if tokens else ""


def build_image_contract(
    scene_output: Dict[str, Any],
    research_payload: Dict[str, Any] | None = None,
) -> Dict[str, object]:
    scenes = list(scene_output.get("scenes", []))
    default_style = "isometric_3d"
    images = []
    for scene in scenes:
        scene_id = str(scene.get("scene_id", ""))
        objective = str(scene.get("objective", "")).strip()
        refs = scene.get("script_refs", [])
        first_ref = str(refs[0]) if isinstance(refs, list) and refs else ""

        composition = objective or first_ref or "Economy explainer visual panel"
        overlay = _derive_overlay_from_ref(first_ref)

        images.append(
            {
                "scene_id": scene_id,
                "asset_id": f"{scene_id}-img",
                "composition": composition,
                "style_profile": default_style,
                "overlay_spec": overlay,
                "schema_version": "1.0",
            }
        )

    return {"images": images, "schema_version": "1.0"}
