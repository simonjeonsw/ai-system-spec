import json
import os
import sys
from pathlib import Path

# Path and library wiring.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
from .storage_utils import normalize_video_id, save_json
from dotenv import load_dotenv
import re

load_dotenv()

class ContentScripter:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.5-flash-lite"

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

    def write_full_script(self, topic):
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

        # Prompt composition: plan + evaluator feedback
        script_prompt = f"""
        # ROLE: professional YouTube Scriptwriter (Channel: Finance Explainer)
        # TASK: Produce a JSON-only script output based on the approved plan and evaluator feedback.

        [APPROVED PLAN]
        {plan_data['plan_content']}

        [EVALUATOR FEEDBACK]
        {plan_data.get('eval_result', 'No specific feedback')}

        --- WRITING RULES ---
        1. Language: Natural, conversational English.
        2. Tone: Kind but incisive.
        3. Reflection: Actively apply the 'Optimization Tips' from the evaluator (e.g., condensing the hook, brand integration).
        4. Structure: Include visual cues [Visual] and Narration text [Narration].
        5. Pacing: Maintain the 'Pattern Interrupts' defined in the plan.
        6. Output JSON only with this schema:
           {{
             "script": "...",
             "citations": ["..."],
             "schema_version": "1.0"
           }}
        7. Provide citations for any factual claims when possible.
        """

        try:
            print(f"🎬 Writing script... (topic: {topic})")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=script_prompt
            )
            
            script_payload = extract_json(response.text)
            if isinstance(script_payload.get("script"), list):
                script_payload["script"] = "\n".join(
                    f"[{item.get('type', 'line').upper()}] {item.get('content', '').strip()}"
                    for item in script_payload["script"]
                ).strip()
            ensure_schema_version(script_payload, "1.0")
            validate_payload("script_output", script_payload)

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
