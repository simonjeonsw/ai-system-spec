import os
import sys
from pathlib import Path

# Path configuration.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from .supabase_client import supabase
from .run_logger import build_metrics, emit_run_log
from .model_router import ModelRouter
from dotenv import load_dotenv
import re

load_dotenv()

class ContentEvaluator:
    def __init__(self):
        self.router = ModelRouter.from_env()

    def extract_video_id(self, url):
        """Extract the 11-char YouTube video ID."""
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else url

    def fetch_latest_plan(self, topic):
        """Fetch the latest planner output."""
        video_id = self.extract_video_id(topic)
        print(f"🔍 Looking up plan in DB... (ID: {video_id})")
        
        # Use descending order for latest entry.
        res = supabase.table("planning_cache") \
            .select("*") \
            .ilike("topic", f"%{video_id}%") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        return res.data[0] if res.data else None

    def evaluate_plan(self, topic):
        plan_data = self.fetch_latest_plan(topic)
        
        if not plan_data:
            emit_run_log(
                stage="qa",
                status="failure",
                input_refs={"topic": topic},
                error_summary="planning_cache entry not found",
                metrics=build_metrics(cache_hit=False),
            )
            return "❌ Plan not found in DB. Run the planner stage first."

        # Evaluation criteria based on prompts/evaluator.md
        eval_prompt = f"""
        # ROLE: Viral Content Quality Auditor
        # TASK: Evaluate the following YouTube plan based on strict viral criteria.
        
        [PLAN TO EVALUATE]
        {plan_data['plan_content']}

        --- EVALUATION CRITERIA (FROM prompts/evaluator.md) ---
        1. [CTR]: Are the titles and thumbnails high-curiosity?
        2. [RETENTION]: Does the hook (0-30s) effectively create an open loop?
        3. [STRUCTURE]: Are there pattern interrupts every 2-3 mins?
        4. [FEASIBILITY]: Is this script producible for our channel?

        --- OUTPUT FORMAT (ENGLISH) ---
        - Status: [PASS / FAIL / NEEDS REVISION]
        - Score: (0-100)
        - Critical Flaws: (List if any)
        - Optimization Tips: (Specific advice for improvement)
        """

        try:
            print("🧐 Running plan evaluation...")
            response_text = self.router.generate_content(eval_prompt)
            
            # Update evaluation result
            supabase.table("planning_cache").update({
                "eval_result": response_text
            }).eq("id", plan_data['id']).execute()

            emit_run_log(
                stage="qa",
                status="success",
                input_refs={"topic": topic},
                output_refs={"planning_cache": plan_data["id"]},
                metrics=build_metrics(cache_hit=False),
            )
            return response_text
        except Exception as e:
            emit_run_log(
                stage="qa",
                status="failure",
                input_refs={"topic": topic},
                error_summary=str(e),
                metrics=build_metrics(cache_hit=False),
            )
            return f"❌ Evaluation failed: {str(e)}"

if __name__ == "__main__":
    evaluator = ContentEvaluator()
    print("\n" + "="*50)
    print("⚖️ [EVALUATOR] Quality review stage")
    target_input = input("👉 Enter a video URL or ID to evaluate: ").strip()
    
    if target_input:
        result = evaluator.evaluate_plan(target_input)
        print("\n" + "="*50)
        print("📋 Evaluation report:\n")
        print(result)
