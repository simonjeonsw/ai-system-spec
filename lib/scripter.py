import os
import sys
from pathlib import Path

# 경로 설정 및 라이브러리 연동 (더블체크 완료)
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
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
        """승인된 기획안과 검수 결과(피드백)를 소환"""
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
            return "❌ 승인된 기획안이 없습니다. Evaluator 공정을 먼저 통과시켜주세요."

        # 프롬프트 구성: 기획안 + 검수 피드백 반영
        script_prompt = f"""
        # ROLE: professional YouTube Scriptwriter (Channel: 유치한 경제학)
        # TASK: Write a word-for-word narration script based on the approved plan and evaluator feedback.

        [APPROVED PLAN]
        {plan_data['plan_content']}

        [EVALUATOR FEEDBACK]
        {plan_data.get('eval_result', 'No specific feedback')}

        --- WRITING RULES ---
        1. Language: Natural, conversational KOREAN (구어체).
        2. Tone: Kind but sharp (친절하지만 날카로운 통찰).
        3. Reflection: Actively apply the 'Optimization Tips' from the evaluator (e.g., condensing the hook, brand integration).
        4. Structure: Include visual cues [Visual] and Narration text [Narration].
        5. Pacing: Maintain the 'Pattern Interrupts' defined in the plan.
        """

        try:
            print(f"🎬 최종 대본 집필 중... (대상: {topic})")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=script_prompt
            )
            
            # 대본 결과 저장 (컬럼이 없다면 추가가 필요할 수 있음)
            # 여기서는 편의상 planning_cache의 새로운 컬럼이나 별도 로그로 처리 가능
            # 일단 결과 반환에 집중합니다.
            return response.text
        except Exception as e:
            return f"❌ 대본 집필 중 오류 발생: {str(e)}"

if __name__ == "__main__":
    scripter = ContentScripter()
    print("\n" + "="*50)
    print("✍️ [SCRIPTER] 상세 대본 집필 공정 가동")
    target_input = input("👉 대본을 쓸 영상의 URL 또는 ID를 입력하세요: ").strip()
    
    if target_input:
        script = scripter.write_full_script(target_input)
        print("\n" + "="*50)
        print("📜 최종 완성 대본:\n")
        print(script)