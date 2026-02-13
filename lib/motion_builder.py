"""Build motion contracts from static image contracts."""

from __future__ import annotations

from typing import Dict, List


_ENTRANCE = ["fade_in", "slide_up", "scale_in"]
_EMPHASIS = ["none", "micro_shake", "slow_zoom"]
_EXIT = ["hard_cut", "fade_out", "cross_dissolve"]


def build_motion_contract(image_contract: Dict[str, object]) -> Dict[str, object]:
    images = list(image_contract.get("images", []))
    motions: List[Dict[str, str]] = []
    for idx, image in enumerate(images, start=1):
        scene_id = str(image.get("scene_id", f"s{idx:02d}"))
        asset_id = str(image.get("asset_id", f"{scene_id}-img"))
        motions.append(
            {
                "scene_id": scene_id,
                "asset_id": asset_id,
                "entrance": _ENTRANCE[(idx - 1) % len(_ENTRANCE)],
                "emphasis": _EMPHASIS[(idx - 1) % len(_EMPHASIS)],
                "exit": _EXIT[(idx - 1) % len(_EXIT)],
                "schema_version": "1.0",
            }
        )
    return {"motions": motions, "schema_version": "1.0"}
