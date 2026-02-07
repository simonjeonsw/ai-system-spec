import os
import sys
from pathlib import Path

# 경로 설정 (기존 설정 유지)
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from .run_logger import emit_run_log
from dotenv import load_dotenv
import re

load_dotenv()

class ContentEvaluator:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.eval_model = "gemini-2.5-flash-lite"

    def extract_video_id(self, url):
        """URL에서 11자리 비디오 ID 추출 (Planner와 로직 통일)"""
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else url

    def fetch_latest_plan(self, topic):
        """planner.py가 저장한 최신 기획안 소환"""
        video_id = self.extract_video_id(topic)
        print(f"🔍 DB에서 기획안 찾는 중... (ID: {video_id})")
        
        # ⚠️ 오류 수정: order("created_at", desc=True)로 변경하여 호환성 확보
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
            )
            return "❌ 검수할 기획안을 DB에서 찾을 수 없습니다. 플래너(planner.py)를 먼저 가동해주세요."

        # prompts/evaluator.md의 핵심 기준 반영
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

        --- OUTPUT FORMAT (KOREAN) ---
        - Status: [PASS / FAIL / NEEDS REVISION]
        - Score: (0-100)
        - Critical Flaws: (List if any)
        - Optimization Tips: (Specific advice for improvement)
        """

        try:
            print(f"🧐 기획안 최종 검수 시작... (모델: {self.eval_model})")
            response = self.client.models.generate_content(
                model=self.eval_model,
                contents=eval_prompt
            )
            
            # 검수 결과 DB 업데이트
            supabase.table("planning_cache").update({
                "eval_result": response.text
            }).eq("id", plan_data['id']).execute()

            emit_run_log(
                stage="qa",
                status="success",
                input_refs={"topic": topic},
                output_refs={"planning_cache": plan_data["id"]},
            )
            return response.text
        except Exception as e:
            emit_run_log(
                stage="qa",
                status="failure",
                input_refs={"topic": topic},
                error_summary=str(e),
            )
            return f"❌ 검수 공정 중 오류 발생: {str(e)}"

if __name__ == "__main__":
    evaluator = ContentEvaluator()
    print("\n" + "="*50)
    print("⚖️ [EVALUATOR] 품질 검수 공정 가동")
    target_input = input("👉 검수할 영상의 URL 또는 ID를 입력하세요: ").strip()
    
    if target_input:
        result = evaluator.evaluate_plan(target_input)
        print("\n" + "="*50)
        print("📋 최종 검수 보고서:\n")
        print(result)
