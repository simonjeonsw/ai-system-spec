import os
import sys
from pathlib import Path

# 가상환경 및 라이브러리 경로 유지
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

class ContentPlanner:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 안정적인 기획을 위해 main_model(2.0-flash) 사용
        self.main_model = "gemini-2.0-flash"

    def fetch_research_data(self, topic):
        """리서처가 수집한 모든 데이터(대본, 분석, 댓글 등)를 가져옴"""
        res = supabase.table("research_cache").select("*").eq("topic", topic).execute()
        return res.data[0] if res.data else None

    def create_project_plan(self, topic, target_persona="친절하지만 날카로운 통찰력을 가진 지식 전달자"):
        """리서치 원료를 바탕으로 터지는 영상을 위한 전략 기획안 작성"""
        
        # 1. 원료 확보
        research_data = self.fetch_research_data(topic)
        if not research_data:
            return "❌ 리서치 데이터가 없습니다. 먼저 리서치 공정(VideoResearcher)을 가동해주세요."

        # 2. 전략기획형 프롬프트 (대본 공학 및 알고리즘 최적화 반영)
        # [최종 보정] 지시문은 영어로(Logic), 출력은 한글로(Content)
        prompt_text = f"""
        # ROLE: World-class YouTube Content Strategist & Scriptwriter
        # TASK: Create a high-performance video production plan based on research data.
        
        [INPUT DATA]
        - Topic: {research_data['topic']}
        - Research Analysis: {research_data['deep_analysis']}
        - Raw Transcript: {research_data.get('raw_transcript', 'N/A')[:3000]}

        --- SYSTEM INSTRUCTIONS ---
        1. PERSOAN: {target_persona}
        2. GOAL: Maximize AVD (Average View Duration) and CTR (Click-Through Rate).
        3. OUTPUT LANGUAGE: All content must be written in KOREAN, but technical terms can be in English.

        --- REQUIRED OUTPUT SECTIONS ---
        
        1. [Title & Thumbnail Strategy]
           - Suggest 3 high-CTR titles in Korean.
           - Describe visual thumbnail concepts that evoke curiosity or FOMO.

        2. [Retention-Driven Script Structure]
           - 0~30s (Hook): Define the specific promise and stakes.
           - Pacing: Plan 'Pattern Interrupts' every 2-3 minutes to maintain tension.

        3. [Master Script Draft (KOREAN)]
           - Write a full script draft using the tone of {target_persona}.
           - Include visual cues and easy metaphors.

        4. [Shorts Expansion]
           - Recommend 2 highlight moments for YouTube Shorts with specific hook lines.

        5. [Executive Summary (ENGLISH)]
           - Brief strategic overview for reference.
        """

        print(f"🚀 전략기획 공정 가동 중... (대상: {topic})")
        
        try:
            # 3. AI 기획안 생성 (Gemini 호출)
            response = self.client.models.generate_content(
                model=self.main_model,
                contents=prompt_text
            )
            plan_result = response.text

            # 4. 기획안 저장 (planning_cache 테이블)
            supabase.table("planning_cache").insert({
                "topic": topic,
                "plan_content": plan_result
            }).execute()

            return plan_result

        except Exception as e:
            return f"❌ 기획 공정 중 오류 발생: {str(e)}"

def fetch_research_data(self, topic):
        """URL의 일부만 맞아도 데이터를 가져오도록 유연하게 검색"""
        # topic 전체 일치 검색
        res = supabase.table("research_cache").select("*").eq("topic", topic).execute()
        
        # 만약 전체 일치로 안 나오면, ID(마지막 11자)만 추출해서 검색 시도
        if not res.data and len(topic) > 11:
            video_id = topic.split("v=")[-1].split("&")[0] if "v=" in topic else topic.split("/")[-1]
            print(f"🔍 전체 URL로 검색 실패. ID({video_id})로 재검색 중...")
            res = supabase.table("research_cache").select("*").ilike("topic", f"%{video_id}%").execute()
            
        return res.data[0] if res.data else None

# --- 파일 하단 실행부(Main)를 리서처와 똑같이 입력 방식으로 변경 ---
if __name__ == "__main__":
    planner = ContentPlanner()
    
    print("\n" + "="*50)
    print("🚀 [PLANNING STAGE] 유튜브 기획 공정 가동")
    target_url = input("👉 기획할 유튜브 URL을 입력하세요 (리서치가 완료된 것): ").strip()
    
    if target_url:
        # 기획안 생성 실행
        result = planner.create_project_plan(target_url)
        print("\n" + "="*50)
        print("📝 생성된 기획안:\n")
        print(result)