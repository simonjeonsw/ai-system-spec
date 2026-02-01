import os
from .supabase_client import supabase
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

class ContentPlanner:
    def get_latest_research(self):
        """DB에서 최신 리서치 분석 데이터를 가져옴"""
        res = supabase.table("research_cache")\
            .select("*")\
            .eq("topic", "youtube_benchmarking")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return res.data[0] if res.data else None

    def create_video_plan(self):
        research = self.get_latest_research()
        if not research:
            return "No research data found."

        ai_insight = research['deep_analysis']['ai_insight']
        
        prompt = f"""
        Based on this viral video analysis:
        {ai_insight}
        
        Create a new video plan for our channel:
        1. Viral Title: 3 variations
        2. 3-Second Hook Script: Write the exact opening lines.
        3. Main Structure: 3-5 key points.
        4. Thumbnail Strategy: Visual description and text overlay.
        
        Write in Korean, very engaging style.
        """
        
        response = model.generate_content(prompt)
        plan_text = response.text
        
        # Supabase 'scripts' 테이블에 저장
        supabase.table("scripts").insert({
            "title": f"Plan based on {research['title']}",
            "content": plan_text,
            "topic": "youtube_plan"
        }).execute()
        
        return plan_text

if __name__ == "__main__":
    planner = ContentPlanner()
    print("Generating Final Video Plan...")
    print(planner.create_video_plan())