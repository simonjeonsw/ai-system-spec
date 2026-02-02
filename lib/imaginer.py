import os
import sys
from pathlib import Path

# 경로 및 라이브러리 연동 (더블체크 완료)
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
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
        """DB에서 최신 대본 및 기획안 데이터를 가져옴"""
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
            return "❌ 대본 데이터를 찾을 수 없습니다. Scripter 공정을 먼저 완료해주세요."

        # 프롬프트 구성: 썸네일 전략 + 대본의 시각 요소를 결합
        # ⚠️ 변경된 부분: Style 규칙을 3D Isometric으로 업데이트
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
            print(f"🎨 시각 에셋 프롬프트 생성 중... (스타일: 3D Isometric, 대상: {topic})")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt_text
            )
            
            # 결과 저장 (별도 컬럼이나 로그에 저장 권장)
            # 여기서는 결과를 화면에 출력하고 나중에 DB 확장을 고려합니다.
            return response.text
        except Exception as e:
            return f"❌ 프롬프트 생성 중 오류 발생: {str(e)}"

if __name__ == "__main__":
    imaginer = ContentImaginer()
    print("\n" + "="*50)
    print("🎨 [IMAGINER] 시각 에셋 기획 공정 가동")
    target_input = input("👉 프롬프트를 생성할 영상의 URL 또는 ID를 입력하세요: ").strip()
    
    if target_input:
        prompts = imaginer.generate_image_prompts(target_input)
        print("\n" + "="*50)
        print("📸 생성된 AI 이미지 프롬프트:\n")
        print(prompts)