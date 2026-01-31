# System Architecture

## 1. High-Level Architecture
User / Operator
 → Control Plane
 → Agent Orchestrator
 → Specialized Agents
 → Content Pipeline
 → Evaluation Layer
 → Publishing & Analytics

## 2. Control Plane
- Spec Loader
- Global Project Memory
- State Management
- GitHub Integration
- MCP Context Injection

## 3. Observability
- Agent output logs
- Performance metrics
- Error tracking
- Retry and escalation counters

## 4. Data Flow
Research
 → Script
 → Scene Structuring
 → Visual Design
 → Voice
 → Video Assembly
 → QA
 → Upload
 → Performance Feedback

## 5. Failure Handling
- Agent failure → retry
- Quality failure → rewrite
- Pipeline failure → rollback

- ## 🏗 System Architecture (Cost-Efficient)

### 1. Efficiency Layer (신설)
* **Request De-duplicator:** 동일한 주제의 리서치 요청 시 API를 호출하지 않고 로컬 SQLite에서 기존 대본을 불러옴.
* **Token Budgeter:** 각 에이전트별 토큰 사용량을 감시하여 일일 무료 할당량의 80% 도달 시 알림 및 로컬 모델로 전환.

### 2. Workflow Pipeline
1.  **Planner (DeepSeek):** 유튜브 트렌드 분석 및 기획안 작성.
2.  **Cache Check:** 로컬 DB에 유사 콘텐츠 존재 여부 확인.
3.  **Researcher (Gemini Flash):** 실시간 정보 수집 및 팩트 체크.
4.  **Producer (Local Python):** Edge-TTS를 이용한 음성 생성 및 자막 파일(.srt) 생성.
5.  **Human-in-the-loop:** 최종 렌더링 전 사용자 컨펌 (무료 모델의 낮은 정확도 보완).
