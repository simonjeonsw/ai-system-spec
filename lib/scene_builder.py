import json
import os
import sys
from pathlib import Path

# Keep virtual environment path if used locally.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client

from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload


class SceneBuilder:
    def __init__(self) -> None:
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.0-flash"

    def build_scenes(self, research_payload: dict) -> dict:
        validate_payload("research_output", research_payload)

        prompt_text = (
            "You are a Scene Builder. Convert the research JSON into scene outputs.\n"
            "Return JSON only. Do not include commentary.\n"
            "Constraints:\n"
            "- Max 6 scenes.\n"
            "- Every scene has narrative_role: hook, proof, insight, or payoff.\n"
            "- Each claim must map to sources from research.\n"
            "- Include schema_version in each scene.\n"
            "\n"
            "Research JSON:\n"
            f"{json.dumps(research_payload, ensure_ascii=False)}"
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt_text,
        )
        scene_output = extract_json(response.text)
        if "scenes" in scene_output:
            for scene in scene_output["scenes"]:
                ensure_schema_version(scene, "1.0")
                validate_payload("scene_output", scene)
        else:
            raise ValueError("Scene output missing 'scenes' array.")
        return scene_output


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m lib.scene_builder <research_json_path>", file=sys.stderr)
        return 1

    research_path = Path(sys.argv[1])
    research_payload = json.loads(research_path.read_text(encoding="utf-8"))
    builder = SceneBuilder()

    try:
        scene_output = builder.build_scenes(research_payload)
        emit_run_log(
            stage="scene_builder",
            status="success",
            input_refs={"research_path": str(research_path)},
            metrics=build_metrics(cache_hit=False),
        )
        print(json.dumps(scene_output, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="scene_builder",
            status="failure",
            input_refs={"research_path": str(research_path)},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Scene build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
