# Implementation Blueprint — Self-Evolving YouTube Content OS

## Purpose
This document is a persistent handoff blueprint so a new session or a different agent can continue implementation without ambiguity.

## Canonical Agreements (Locked)
1. Pipeline order: `research → plan → script → scene → image → motion → metadata → validate`
2. Strict stage contracts:
   - Scene: structure & timing only
   - Image: static visual assets only
   - Motion: temporal animation only
3. L0–L3 layering model is authoritative.

## Current Runtime State
- Runtime includes a compatibility bridge that transforms legacy raw scene payloads into separate Scene/Image/Motion contracts.
- Validators enforce forbidden fields for stage boundary integrity.

## Critical Note (Must Preserve)
현재 분리 로직은 runtime에서 기존 raw scene(visual 성격 포함)을 받아 contract 분리하는 compatibility bridge입니다. 장기적으로는 scene 생성 원천 자체를 structure-only로 바꾸는 2차 정리가 필요합니다. 그렇지 않으면 “분리는 되었지만 upstream 오염이 계속 유입”되는 형태로 유지보수 비용이 다시 증가합니다.

## Design Table (Implementation-Ready)
| Module | Stage | Responsibility | Primary I/O | Contract Guard | Tests |
| --- | --- | --- | --- | --- | --- |
| `lib/researcher.py` | research | Evidence-backed research payload generation | in: video/topic, out: `research_output` | no script/scene/image/motion fields | schema + source mapping tests |
| `lib/planner.py` | plan | Topic/business prioritization | in: research, out: `planner_output` | no script/rendering fields | score/rubric + schema tests |
| `lib/scripter.py` | script | Semantic source of truth text | in: plan/research, out: `script_output` | no scene timing/image/motion fields | citation + semantic tests |
| `lib/scene_contract_builder.py` | scene | Build structure-only scene contract | in: raw scene-like payload, out: structure-only `scenes[]` | forbid visual/motion-owned fields | scene contract unit tests |
| `lib/image_builder.py` | image | Build static visual contract | in: scene contexts, out: `images[]` | forbid timing/motion fields | image contract unit tests |
| `lib/motion_builder.py` | motion | Build temporal motion contract | in: image contract, out: `motions[]` | forbid scene/script/static composition fields | motion contract unit tests |
| `lib/metadata_generator.py` | metadata | Publish packaging metadata | in: plan+script, out: metadata payload | no upstream semantic mutation | metadata schema/consistency tests |
| `lib/schema_validator.py` | validate-core | Schema + forbidden field enforcement | in: payload, out: pass/fail | contract boundary enforcement | positive/negative forbidden field tests |
| `lib/validation_runner.py` | validate | Stage/all artifact validation | in: artifact files, out: gate result | canonical stage artifact checks | e2e stage validation tests |
| `lib/pipeline_runner.py` | orchestrator | Stage ordering, cache/retry/logging, artifact emission | in: video_id, out: all stage artifacts + manifest | no stage reordering; regeneration scope policy | orchestration integration tests |

## Runtime Artifact Contract
- `data/{video_id}_research.json`
- `data/{video_id}_plan.json`
- `data/{video_id}_script.json` (`script_long`, `script_shorts` as applicable)
- `data/{video_id}_scenes.json` (structure-only)
- `data/{video_id}_image.json`
- `data/{video_id}_motion.json`
- `data/{video_id}_metadata.json`
- `data/{video_id}_validation_report.json`
- `data/{video_id}_pipeline.json`

## 2nd-Phase Cleanup Blueprint (Bridge Removal)

### Goal
Remove compatibility bridge and make scene generation source itself structure-only.

### Steps
1. Convert scene generation source function to emit structure-only fields directly.
2. Ensure image generation consumes only scene contract and style config.
3. Ensure motion generation consumes only image + scene IDs.
4. Remove legacy visual keys from scene generation internals.
5. Lock with CI checks for forbidden fields in stage outputs.

### Exit Criteria
- Scene stage emits no image/motion-owned fields in any runtime path.
- Bridge adapter is removable without behavior regression.
- Stage-specific test suites pass independently (reduced integration-only dependency).

## This was not asked, but is important because...
현재 `pipeline_runner` 내부에 scene/image/motion 변환이 함께 존재하면, 장기적으로 “계약은 분리됐지만 코드 책임은 결합된(monolithic orchestrator)” 상태가 됩니다.

이걸 그대로 두면 10x 규모에서 생기는 문제:
- 변경 영향 분석 난이도 급상승
- stage별 장애 격리 실패
- 테스트 피라미드 붕괴(통합테스트 편중)

즉, 다음 마일스톤에서 **모듈 경계 분리(파일 단위)**를 반드시 하셔야 self-evolving OS의 유지비가 선형으로 유지됩니다.

## Next Actions Checklist
- [ ] Add dedicated unit tests for `scene_contract_builder`, `image_builder`, `motion_builder`
- [ ] Add contract drift CI check for forbidden fields per stage artifact
- [ ] Add regeneration matrix integration assertions for each upstream stage change
- [ ] Remove bridge once scene source is structure-only
