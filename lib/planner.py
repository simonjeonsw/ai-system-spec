import json
import os
import sys
from pathlib import Path

# Keep virtual environment path if used locally.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from .supabase_client import supabase
from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
from .storage_utils import normalize_video_id, save_json
from .model_router import ModelRouter
from dotenv import load_dotenv

load_dotenv()

class ContentPlanner:
    def __init__(self):
        self.router = ModelRouter.from_env()

    def fetch_research_data(self, topic):
            """Fetch cached research by full topic or URL fragment."""
            # Full-topic match
            normalized_topic = normalize_video_id(topic)
            res = supabase.table("research_cache").select("*").eq("topic", normalized_topic).execute()
            
            # If no full match, try by video ID.
            if not res.data and len(topic) > 11:
                video_id = topic.split("v=")[-1].split("&")[0] if "v=" in topic else topic.split("/")[-1]
                print(f"🔍 Full URL lookup failed. Retrying with ID ({video_id})...")
                res = supabase.table("research_cache").select("*").ilike("topic", f"%{video_id}%").execute()
                
            return res.data[0] if res.data else None

    def load_research_payload(self, topic: str) -> dict | None:
        research_data = self.fetch_research_data(topic)
        if not research_data:
            return None
        content = research_data.get("content")
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return extract_json(content)

    def create_project_plan(self, topic, target_persona="insightful finance explainer"):
        """Create a planner output that matches the planner_output schema."""
        normalized_topic = normalize_video_id(topic)
        # 1. Load research payload
        research_payload = self.load_research_payload(normalized_topic)
        if not research_payload:
            return "❌ Research data not found. Run the research stage first."

        # 2. Planner prompt (English JSON output only)
        prompt_text = f"""
        You are the Planner agent. Return JSON only that matches this schema:
        {{
          "topic_candidates": [{{"topic": "...", "scores": {{"audience_fit": 0, "novelty": 0, "monetization_potential": 0, "evidence_availability": 0, "production_feasibility": 0}}, "total_score": 0, "notes": "..."}}],
          "topic": "...",
          "target_audience": "...",
          "business_goal": "...",
          "monetization_angle": "...",
          "retention_hypothesis": "...",
          "content_constraints": ["..."],
          "research_requirements": ["..."],
          "selection_rationale": "...",
          "schema_version": "1.0"
        }}

        Constraints:
        - Output English only.
        - Provide 3-5 topic_candidates with scores from 1-5 and total_score.
        - Select the highest scoring topic and justify selection_rationale.
        - Use target persona: {target_persona}.

        Research JSON:
        {json.dumps(research_payload, ensure_ascii=False)}
        """

        print(f"🚀 Planning stage running... (topic: {normalized_topic})")
        
        try:
            # 3. Generate planner output
            response_text = self.router.generate_content(prompt_text)
            plan_payload = self._parse_with_retry(prompt_text, response_text)
            ensure_schema_version(plan_payload, "1.0")
            validate_payload("planner_output", plan_payload)

            # 4. Store planner output
            supabase.table("planning_cache").upsert(
                {
                    "topic": normalized_topic,
                    "plan_content": json.dumps(plan_payload, ensure_ascii=False),
                },
                on_conflict="topic",
            ).execute()
            save_json("planner", normalized_topic, plan_payload)

            emit_run_log(
                stage="planner",
                status="success",
                input_refs={"topic": normalized_topic},
                output_refs={"planning_cache": "inserted"},
                metrics=build_metrics(cache_hit=False),
            )
            return json.dumps(plan_payload, ensure_ascii=False, indent=2)

        except Exception as e:
            emit_run_log(
                stage="planner",
                status="failure",
                input_refs={"topic": normalized_topic},
                error_summary=str(e),
                metrics=build_metrics(cache_hit=False),
            )
            return f"❌ Planner stage failed: {str(e)}"

    def _parse_with_retry(self, prompt_text: str, response_text: str, max_attempts: int = 2) -> dict:
        try:
            return extract_json(response_text)
        except Exception:
            if max_attempts <= 1:
                raise
            repair_prompt = (
                "Return ONLY valid JSON. Ensure all commas and quotes are correct. "
                "Do not include commentary. Output must match the schema exactly.\n"
            )
            retry_text = self.router.generate_content(repair_prompt + prompt_text)
            return extract_json(retry_text)



# --- CLI entrypoint ---
if __name__ == "__main__":
    planner = ContentPlanner()
    
    print("\n" + "="*50)
    print("🚀 [PLANNING STAGE] YouTube planning stage")
    target_url = input("👉 Enter a YouTube URL (research must be completed): ").strip()
    
    if target_url:
        normalized_topic = normalize_video_id(target_url)
        cached = supabase.table("planning_cache").select("*").eq("topic", normalized_topic).execute()
        force_refresh = False
        if cached.data:
            choice = input("Existing data found. Use cached data or force a refresh? (y/n): ").strip().lower()
            force_refresh = choice == "n"

        if cached.data and cached.data[0].get("plan_content") and not force_refresh:
            try:
                cached_payload = json.loads(cached.data[0]["plan_content"])
                save_json("planner", normalized_topic, cached_payload)
                result = json.dumps(cached_payload, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                result = cached.data[0]["plan_content"]
        else:
            result = planner.create_project_plan(normalized_topic)
        print("\n" + "="*50)
        print("📝 Generated plan:\n")
        print(result)
