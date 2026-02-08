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

class ContentImaginer:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.5-flash-lite"

    def extract_video_id(self, url):
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else url

    def fetch_script_data(self, topic):
        """Fetch the latest plan data from the database."""
        video_id = self.extract_video_id(topic)
        res = supabase.table("planning_cache") \
            .select("*") \
            .ilike("topic", f"%{video_id}%") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None

    def generate_image_prompts(self, topic):
        data = self.fetch_script_data(topic)
        
        if not data:
            emit_run_log(
                stage="visual",
                status="failure",
                input_refs={"topic": topic},
                error_summary="script data not found",
                metrics=build_metrics(cache_hit=False),
            )
            return "❌ Script data not found. Run the scripter stage first."

        # Prompt composition: thumbnail strategy + visual cues from plan
        # Style rule: 3D Isometric
        prompt_text = f"""
        # ROLE: Expert AI Image Prompt Engineer for YouTube
        # TASK: Create 3 high-performance image prompts (1 for Thumbnail, 2 for Key Visuals in Video).

        [CONTEXT]
        - Topic: {data['topic']}
        - Core Plan: {data['plan_content']}

        --- INSTRUCTIONS ---
        1. Create detailed English prompts for DALL-E 3 or Midjourney.
        2. Format: [Prompt Name], [Prompt Text], [Reasoning].
        3. Style: **Vibrant 3D Isometric illustration, clean lines, friendly cartoonish style, focused on "Financial Success" and "Compounding Magic". Use bright, appealing colors with soft shadows.**
        4. No text in images (unless specified as a graphic element).
        """

        try:
            print(f"🎨 Generating visual asset prompts... (style: 3D Isometric, topic: {topic})")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt_text
            )
            
            # Consider storing results in a dedicated table or log.
            emit_run_log(
                stage="visual",
                status="success",
                input_refs={"topic": topic},
                metrics=build_metrics(cache_hit=False),
            )
            return response.text
        except Exception as e:
            emit_run_log(
                stage="visual",
                status="failure",
                input_refs={"topic": topic},
                error_summary=str(e),
                metrics=build_metrics(cache_hit=False),
            )
            return f"❌ Prompt generation failed: {str(e)}"

if __name__ == "__main__":
    imaginer = ContentImaginer()
    print("\n" + "="*50)
    print("🎨 [IMAGINER] Visual asset planning stage")
    target_input = input("👉 Enter a video URL or ID for prompt generation: ").strip()
    
    if target_input:
        prompts = imaginer.generate_image_prompts(target_input)
        print("\n" + "="*50)
        print("📸 Generated AI image prompts:\n")
        print(prompts)
