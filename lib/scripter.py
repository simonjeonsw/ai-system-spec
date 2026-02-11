import json
import os
import sys
from pathlib import Path

# Path and library wiring.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from .supabase_client import supabase
from .json_utils import ensure_schema_version, extract_json_relaxed
from .model_router import ModelRouter
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
from .storage_utils import normalize_video_id, save_json, save_raw
from dotenv import load_dotenv
import re

load_dotenv()

class ContentScripter:
    def __init__(self):
        self.router = ModelRouter.from_env()

    def extract_video_id(self, url):
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else url

    def fetch_approved_plan(self, topic):
        """Fetch the latest approved plan and evaluator feedback."""
        video_id = normalize_video_id(topic)
        res = supabase.table("planning_cache") \
            .select("*") \
            .ilike("topic", f"%{video_id}%") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None

    def write_full_script(
        self,
        topic,
        source_ids: list[str] | None = None,
        mode: str = "long",
    ):
        return self._write_script(topic, feedback=None, source_ids=source_ids, mode=mode)

    def write_full_script_with_feedback(
        self,
        topic,
        feedback: str,
        source_ids: list[str] | None = None,
        mode: str = "long",
    ):
        return self._write_script(topic, feedback=feedback, source_ids=source_ids, mode=mode)

    def _write_script(
        self,
        topic,
        feedback: str | None,
        source_ids: list[str] | None,
        mode: str,
    ):
        plan_data = self.fetch_approved_plan(topic)
        
        if not plan_data:
            emit_run_log(
                stage="script",
                status="failure",
                input_refs={"topic": topic},
                error_summary="approved plan not found",
                metrics=build_metrics(cache_hit=False),
            )
            return "❌ Approved plan not found. Run the evaluator stage first."

        feedback_text = feedback or "No additional feedback."
        target_words = "1300" if mode == "long" else "160"
        target_runtime = "5.5 minutes" if mode == "long" else "55 seconds"
        source_list = ", ".join(source_ids or [])
        # Prompt composition: plan + evaluator feedback
        script_prompt = f"""
        # ROLE: professional YouTube Scriptwriter (Channel: Finance Explainer)
        # TASK: Produce a JSON-only script output based on the approved plan and evaluator feedback.

        [APPROVED PLAN]
        {plan_data['plan_content']}

        [EVALUATOR FEEDBACK]
        {plan_data.get('eval_result', 'No specific feedback')}

        [VALIDATION FEEDBACK]
        {feedback_text}

        [AVAILABLE SOURCE IDS]
        {source_list}

        --- WRITING RULES ---
        1. Language: Natural, conversational English.
        2. Tone: Kind but incisive.
        3. Reflection: Actively apply the 'Optimization Tips' from the evaluator (e.g., condensing the hook, brand integration).
        4. Structure: Include visual cues [Visual] and Narration text [Narration].
        5. Pacing: Use the 3-Step Retention Structure (Negative Hook -> Mid-Reward -> Open Loop).
        6. Runtime target: {target_runtime} (~{target_words} words).
        7. Output JSON only with this schema:
           {{
             "script": "...",
             "citations": ["..."],
             "schema_version": "1.0"
           }}
        8. Use the AVAILABLE SOURCE IDS list. Add inline citations like [src-001] for factual claims.
        9. Ensure at least one cited sentence per section when possible.
        10. Provide citations list that includes the same source_id tokens.
        """

        try:
            print(f"🎬 Writing script... (topic: {topic})")
            response_text = self.router.generate_content(script_prompt)
            video_id = normalize_video_id(topic)
            raw_stage = "script_long_raw" if mode == "long" else "script_shorts_raw"
            save_raw(raw_stage, video_id, response_text)
            script_payload = extract_json_relaxed(response_text)
            if isinstance(script_payload.get("script"), list):
                script_payload["script"] = "\n".join(
                    f"[{item.get('type', 'line').upper()}] "
                    f"{str(item.get('content') or item.get('narration') or '').strip()}"
                    for item in script_payload["script"]
                ).strip()
            elif isinstance(script_payload.get("script"), dict):
                script_payload["script"] = json.dumps(
                    script_payload["script"],
                    ensure_ascii=False,
                )
            if not isinstance(script_payload.get("script"), str):
                script_payload["script"] = str(script_payload.get("script", ""))
            if isinstance(script_payload.get("citations"), list):
                script_payload["citations"] = [
                    item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                    for item in script_payload["citations"]
                ]
            ensure_schema_version(script_payload, "1.0")
            try:
                validate_payload("script_output", script_payload)
            except Exception as exc:
                emit_run_log(
                    stage="script",
                    status="warning",
                    input_refs={"topic": topic},
                    error_summary=f"script schema warning: {exc}",
                    metrics=build_metrics(cache_hit=False),
                )
            word_count = len(script_payload.get("script", "").split())
            if mode == "long" and word_count < 1100:
                script_payload = self._extend_script(script_payload, target_words)
            if mode == "shorts" and word_count > 180:
                script_payload = self._enforce_shorts_length(script_payload, target_words)
            ensure_schema_version(script_payload, "1.0")
            try:
                validate_payload("script_output", script_payload)
            except Exception as exc:
                emit_run_log(
                    stage="script",
                    status="warning",
                    input_refs={"topic": topic},
                    error_summary=f"script schema warning: {exc}",
                    metrics=build_metrics(cache_hit=False),
                )

            # Consider storing script results in a dedicated table.
            emit_run_log(
                stage="script",
                status="success",
                input_refs={"topic": topic},
                metrics=build_metrics(cache_hit=False),
            )
            return json.dumps(script_payload, ensure_ascii=False, indent=2)
        except Exception as e:
            emit_run_log(
                stage="script",
                status="failure",
                input_refs={"topic": topic},
                error_summary=str(e),
                metrics=build_metrics(cache_hit=False),
            )
            return f"❌ Script generation failed: {str(e)}"

    def _extend_script(self, script_payload: dict, target_words: str) -> dict:
        prompt = f"""
        Expand the following script to reach ~{target_words} words.
        Preserve citations and add more evidence-backed detail where needed.
        Return JSON only with schema:
        {{
          "script": "...",
          "citations": ["..."],
          "schema_version": "1.0"
        }}

        Script JSON:
        {json.dumps(script_payload, ensure_ascii=False)}
        """
        expanded_payload = extract_json_relaxed(self.router.generate_content(prompt))
        if isinstance(expanded_payload.get("script"), list):
            expanded_payload["script"] = "\n".join(
                f"[{item.get('type', 'line').upper()}] "
                f"{str(item.get('content') or item.get('narration') or '').strip()}"
                for item in expanded_payload["script"]
            ).strip()
        elif isinstance(expanded_payload.get("script"), dict):
            expanded_payload["script"] = json.dumps(expanded_payload["script"], ensure_ascii=False)
        if not isinstance(expanded_payload.get("script"), str):
            expanded_payload["script"] = str(expanded_payload.get("script", ""))
        if isinstance(expanded_payload.get("citations"), list):
            expanded_payload["citations"] = [
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                for item in expanded_payload["citations"]
            ]
        return expanded_payload

    def _shrink_script(self, script_payload: dict, target_words: str) -> dict:
        prompt = f"""
        Shorten the following script to ~{target_words} words (hard cap 180 words).
        Preserve citations and keep the strongest hook.
        Return JSON only with schema:
        {{
          "script": "...",
          "citations": ["..."],
          "schema_version": "1.0"
        }}

        Script JSON:
        {json.dumps(script_payload, ensure_ascii=False)}
        """
        shortened_payload = extract_json_relaxed(self.router.generate_content(prompt))
        if isinstance(shortened_payload.get("script"), list):
            shortened_payload["script"] = "\n".join(
                f"[{item.get('type', 'line').upper()}] "
                f"{str(item.get('content') or item.get('narration') or '').strip()}"
                for item in shortened_payload["script"]
            ).strip()
        elif isinstance(shortened_payload.get("script"), dict):
            shortened_payload["script"] = json.dumps(shortened_payload["script"], ensure_ascii=False)
        if not isinstance(shortened_payload.get("script"), str):
            shortened_payload["script"] = str(shortened_payload.get("script", ""))
        if isinstance(shortened_payload.get("citations"), list):
            shortened_payload["citations"] = [
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                for item in shortened_payload["citations"]
            ]
        return shortened_payload

    def _enforce_shorts_length(self, script_payload: dict, target_words: str) -> dict:
        updated_payload = script_payload
        for _ in range(2):
            word_count = len(updated_payload.get("script", "").split())
            if word_count <= 180:
                break
            updated_payload = self._shrink_script(updated_payload, target_words)
        return updated_payload

if __name__ == "__main__":
    scripter = ContentScripter()
    print("\n" + "="*50)
    print("✍️ [SCRIPTER] Script drafting stage")
    target_input = input("👉 Enter a video URL or ID for script drafting: ").strip()
    
    if target_input:
        video_id = normalize_video_id(target_input)
        cached = (
            supabase.table("scripts")
            .select("*")
            .ilike("content", f"%{video_id}%")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        force_refresh = False
        if cached.data:
            choice = input("Existing data found. Use cached data or force a refresh? (y/n): ").strip().lower()
            force_refresh = choice == "n"

        if cached.data and cached.data[0].get("content") and not force_refresh:
            cached_content = cached.data[0]["content"]
            try:
                cached_payload = json.loads(cached_content)
                save_json("script", video_id, cached_payload)
                script = json.dumps(cached_payload, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                script = cached_content
        else:
            script = scripter.write_full_script(video_id)
            try:
                payload = json.loads(script)
                payload["video_id"] = video_id
                supabase.table("scripts").insert({"content": json.dumps(payload, ensure_ascii=False)}).execute()
                save_json("script", video_id, payload)
            except json.JSONDecodeError:
                pass

        print("\n" + "="*50)
        print("📜 Final script:\n")
        print(script)
