import json
import tempfile
import unittest
from pathlib import Path

from lib.schema_validator import validate_payload
from lib.validation_runner import validate_files


class MetadataContractTests(unittest.TestCase):
    def _base_payload(self) -> dict:
        return {
            "title": "Why CPI and Wages Diverge in 2026",
            "description": "A concise macro breakdown with policy context.",
            "tags": ["macro", "economy", "inflation", "wages", "policy"],
            "chapters": [
                {"timecode": "00:00", "title": "Setup"},
                {"timecode": "00:30", "title": "What changed"},
            ],
            "pinned_comment": "What signal do you track most?",
            "pinned_comment_variants": [
                "What signal do you track most?",
                "What signal do you track most? Share your view.",
            ],
            "thumbnail_variants": [
                {"label": "A", "text": "Inflation vs Wages", "visual_brief": "Split chart"},
                {"label": "B", "text": "Policy Shock", "visual_brief": "Central bank silhouette"},
            ],
            "community_post": "New macro explainer just dropped.",
            "community_post_variants": [
                "New macro explainer just dropped.",
                "New macro explainer just dropped. Save this for later.",
            ],
            "estimated_runtime_sec": 180,
            "speech_rate_wpm": 180,
            "schema_version": "1.1",
        }

    def test_metadata_schema_allows_geo_phase_a_placeholders(self) -> None:
        payload = self._base_payload()
        payload.update(
            {
                "target_locale": "ko-KR",
                "target_region": "KR",
                "primary_keyword": "inflation wage gap",
                "secondary_keywords": ["cpi", "real income"],
            }
        )
        validate_payload("metadata_output", payload)

    def test_metadata_schema_supports_missing_geo_phase_a_fields(self) -> None:
        validate_payload("metadata_output", self._base_payload())

    def test_metadata_schema_rejects_undeclared_fields(self) -> None:
        payload = self._base_payload()
        payload["geo_temp_note"] = "should fail"
        with self.assertRaises(ValueError):
            validate_payload("metadata_output", payload)

    def test_metadata_geo_warnings_are_warn_only(self) -> None:
        payload = self._base_payload()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            warnings = validate_files("metadata", [str(path)])
        self.assertGreaterEqual(len(warnings), 2)
        self.assertTrue(any("target_locale" in w for w in warnings))
        self.assertTrue(any("target_region" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
