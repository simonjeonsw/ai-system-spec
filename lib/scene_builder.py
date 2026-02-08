import json
import os
import sys
import time
from pathlib import Path

# Keep virtual environment path if used locally.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client

from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
from .storage_utils import normalize_video_id, save_json
from .supabase_client import supabase


class SceneBuilder:
    def __init__(self) -> None:
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.0-flash"

    def build_scenes(self, research_payload: dict) -> dict:
        validate_payload("research_output", research_payload)

        prompt_text = self._build_prompt(research_payload)
        scene_output = self._generate_with_retry(prompt_text)
        try:
            self._validate_scene_output(scene_output)
            return scene_output
        except ValueError:
            repaired_output = self._repair_scene_output(scene_output, research_payload)
            self._validate_scene_output(repaired_output)
            return repaired_output

    def _build_prompt(self, research_payload: dict, retry: bool = False) -> str:
        reminder = "Ensure every scene includes all required keys." if retry else ""
        return (
            "You are a Scene Builder. Convert the research JSON into scene outputs.\n"
            "Return JSON only. Do not include commentary.\n"
            "Constraints:\n"
            "- Max 6 scenes.\n"
            "- Every scene has narrative_role: hook, proof, insight, or payoff.\n"
            "- Each claim must map to sources from research.\n"
            "- Include schema_version in each scene.\n"
            f"{reminder}\n"
            "\n"
            "Required JSON structure:\n"
            "{\n"
            '  "scenes": [\n'
            "    {\n"
            '      "scene_id": "s1-hook",\n'
            '      "objective": "Establish the core question and stakes.",\n'
            '      "key_claims": ["Claim 1", "Claim 2"],\n'
            '      "source_refs": [{"claim": "Claim 1", "sources": ["src-001"]}],\n'
            '      "evidence_sources": ["src-001"],\n'
            '      "visual_prompt": "Describe the visuals.",\n'
            '      "narration_prompt": "Describe the narration.",\n'
            '      "transition_note": "Explain the transition.",\n'
            '      "narrative_role": "hook",\n'
            '      "schema_version": "1.0"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "Research JSON:\n"
            f"{json.dumps(research_payload, ensure_ascii=False)}"
        )

    def _generate_with_retry(self, prompt_text: str) -> dict:
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt_text,
            )
            return extract_json(response.text)
        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                time.sleep(2)
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt_text,
                )
                return extract_json(response.text)
            raise

    def _validate_scene_output(self, scene_output: dict) -> None:
        if "scenes" in scene_output:
            for scene in scene_output["scenes"]:
                ensure_schema_version(scene, "1.0")
                validate_payload("scene_output", scene)
        else:
            raise ValueError("Scene output missing 'scenes' array.")

    def _repair_scene_output(self, scene_output: dict, research_payload: dict) -> dict:
        prompt_text = self._build_prompt(research_payload, retry=True)
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt_text,
        )
        return extract_json(response.text)


def main() -> int:
    if len(sys.argv) >= 2:
        topic_input = sys.argv[1]
    else:
        topic_input = input("👉 Enter a YouTube URL or ID for scene building: ").strip()

    if not topic_input:
        print("Missing YouTube URL or ID.", file=sys.stderr)
        return 1

    topic = normalize_video_id(topic_input)
    cached_path = Path(__file__).resolve().parent.parent / "data" / f"scene_builder_{topic}.json"
    force_refresh = False
    if cached_path.exists():
        choice = input("Existing data found. Use cached data or force a refresh? (y/n): ").strip().lower()
        force_refresh = choice == "n"

    cached = supabase.table("research_cache").select("*").eq("topic", topic).execute()
    if not cached.data or not cached.data[0].get("content"):
        print("Research data not found in Supabase. Run the research stage first.", file=sys.stderr)
        return 1

    if cached_path.exists() and not force_refresh:
        print(cached_path.read_text(encoding="utf-8"))
        return 0

    research_payload = json.loads(cached.data[0]["content"])
    builder = SceneBuilder()

    try:
        scene_output = builder.build_scenes(research_payload)
        save_json("scene_builder", topic, scene_output)
        emit_run_log(
            stage="scene_builder",
            status="success",
            input_refs={"topic": topic},
            metrics=build_metrics(cache_hit=False),
        )
        print(json.dumps(scene_output, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="scene_builder",
            status="failure",
            input_refs={"topic": topic},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Scene build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
