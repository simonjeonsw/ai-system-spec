# 구조 설계(Structure Design) 스펙

## 목적
연구(Research) 및 기획(Planner) 결과를 **씬/비트 단위 구조**로 변환하는 역할을 정의한다. 이 단계는 영상/콘텐츠의 리듬과 흐름을 설계하며, 다음 단계(Script/Visual/Voice)에 **구조적 청사진**을 제공한다.

## 입력
- Planner/Research 출력 요약(핵심 사실, 논지, 근거, 인사이트)
- 목표 지표(리텐션, 수익 등)

## 출력
- 씬 리스트(타임코드 포함)
  - Hook / Proof / Insight / Payoff 매핑
- 장면별 목적(왜 이 장면이 필요한지)
- 장면별 CTA(Call To Action)
- 시각·음성 힌트(Visual/Voice 힌트)

## 역할 범위(Responsibility)
- **핵심 역할**: 연구 결과를 시청자 경험 단위(씬/비트)로 분해하고, 몰입·설득·전환을 위한 구조를 설계한다.
- **포함 작업**
  - 흐름/리듬 설계(전개, 텐션, 완급 조절)
  - Hook/Proof/Insight/Payoff에 맞는 구조 배치
  - CTA 위치 및 강도 설계
  - 시각/음성 힌트를 통해 후속 단계 이해도 향상
- **제외 작업**
  - 실제 대본 작성(스크립트 문장/대사 작성)
  - 시각 제작(썸네일/그래픽/촬영 세부 설계)
  - 보이스 연기/톤 구체 지시(실제 녹음 지시)

## 경계 및 핸드오프 규칙
- **Script 단계**
  - 전달물: 씬별 목적, 논리 연결, 핵심 메시지/근거, CTA 위치
  - Script는 Structure의 씬 단위를 유지하되, 문장/대사/전개를 구체화한다.
- **Visual 단계**
  - 전달물: 씬별 시각 힌트(그래프/자료/비주얼 메타포), 화면 전환 포인트
  - Visual은 Structure의 힌트를 시각 자산 및 연출 설계로 확장한다.
- **Voice 단계**
  - 전달물: 씬별 음성 힌트(속도, 강조, 감정 톤, 호흡)
  - Voice는 Structure의 의도를 반영해 실제 전달 톤을 설계한다.
- **금지 사항**
  - Structure 단계에서 Script/Visual/Voice의 구체 산출물(완성 문장, 레이아웃, 녹음 지시)을 선행하지 않는다.

## 품질 기준
- 목표 지표(리텐션/수익)에 직접 연결되는 구조적 의사결정이 반영되어야 한다.
- 각 씬은 “목적-근거-CTA”가 명확해야 한다.
- Hook/Proof/Insight/Payoff의 비중과 순서가 명시되어야 한다.
- 씬 간 전환 논리가 끊기지 않아야 한다.

## 필수 출력 스키마
```yaml
structure_design:
  input_summary:
    planner_research_summary: "<요약 텍스트>"
    target_metrics: ["retention", "revenue"]
  scenes:
    - id: 1
      timecode: "00:00-00:20"
      beat_type: "Hook" # Hook | Proof | Insight | Payoff
      purpose: "<장면 목적>"
      key_points:
        - "<핵심 포인트>"
      cta: "<장면 CTA>"
      visual_hints:
        - "<시각 힌트>"
      voice_hints:
        - "<음성 힌트>"
      handoff_notes:
        script: "<스크립트 단계 전달 요점>"
        visual: "<비주얼 단계 전달 요점>"
        voice: "<보이스 단계 전달 요점>"
```
