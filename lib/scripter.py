import os
import sys
from pathlib import Path

# Path and library wiring.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from .run_logger import build_metrics, emit_run_log
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
        video_id = self.extract_video_id(topic)
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
        # TASK: Write a word-for-word narration script based on the approved plan and evaluator feedback.

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
        """

        try:
            print(f"🎬 Writing script... (topic: {topic})")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=script_prompt
            )
            
            # Consider storing script results in a dedicated table.
            emit_run_log(
                stage="script",
                status="success",
                input_refs={"topic": topic},
                metrics=build_metrics(cache_hit=False),
            )
            return response.text
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
        script = scripter.write_full_script(target_input)
        print("\n" + "="*50)
        print("📜 Final script:\n")
        print(script)
