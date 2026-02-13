import unittest

from lib.image_builder import build_image_contract
from lib.motion_builder import build_motion_contract
from lib.scene_source_builder import build_structure_only_scenes
from lib.schema_validator import validate_payload


class ContractBuilderTests(unittest.TestCase):
    def test_scene_source_is_structure_only(self) -> None:
        payload = build_structure_only_scenes(
            [
                {"narration": "Inflation remained above target while wages slowed."},
                {"narration": "Household savings rates dropped to multi-year lows."},
            ]
        )
        self.assertIn("scenes", payload)
        self.assertEqual(len(payload["scenes"]), 2)
        forbidden = {"visual_prompt", "camera_angle", "overlay_text", "style_profile", "animation", "easing"}
        for scene in payload["scenes"]:
            validate_payload("scene_output", scene)
            self.assertTrue(forbidden.isdisjoint(scene.keys()))

    def test_image_motion_contracts_are_schema_valid(self) -> None:
        scene_payload = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "objective": "Explain the wage-inflation spread.",
                    "script_refs": ["Explain the wage-inflation spread."],
                    "start_sec": 0,
                    "end_sec": 14,
                    "transition_note": "Move to policy causes.",
                    "schema_version": "2.0",
                }
            ]
        }
        image_payload = build_image_contract(scene_payload)
        motion_payload = build_motion_contract(image_payload)

        self.assertIn("images", image_payload)
        self.assertIn("motions", motion_payload)
        validate_payload("image_output", image_payload["images"][0])
        validate_payload("motion_output", motion_payload["motions"][0])


if __name__ == "__main__":
    unittest.main()
