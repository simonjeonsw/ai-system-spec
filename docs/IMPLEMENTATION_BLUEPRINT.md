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
- Runtime currently supports Scene/Image/Motion separation and modular builders.
- Forbidden-field validator guards remain mandatory and active.
- Regeneration scope and contract drift controls are mandatory release gates.

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


---

## Milestone 2 — Bridge Removal Execution Ticket Table

| Ticket ID | Order | Task Description | Target File / Module | Expected Input | Expected Output | Dependencies | Difficulty | Risk |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| M2-T01 | 1 | Freeze canonical contract checks before code switch (baseline safety gate). | `lib/schema_validator.py`, `lib/validation_runner.py` | Existing stage artifacts | Explicit pass/fail baseline for scene/image/motion contract fields | None | Low | Medium |
| M2-T02 | 2 | Refactor raw scene source generation to emit structure-only fields directly. Remove visual/camera/style/motion fields from source output path. | `lib/pipeline_runner.py` (`_build_scene_output_from_script`, `_ensure_scene_granularity`) | `script_payload`, `research_payload` | `scene_output` with only: `scene_id`, `objective`, `script_refs`, `start_sec`, `end_sec`, `transition_note`, `schema_version` | M2-T01 | High | High |
| M2-T03 | 3 | Ensure scene hash/regeneration logic depends only on structure semantics. | `lib/pipeline_runner.py` (`_scene_hash`, `_should_regenerate_scenes`) | structure-only scene + script | deterministic scene cache invalidation independent of style fields | M2-T02 | Medium | Medium |
| M2-T04 | 4 | Remove bridge adaptation path from orchestrator once source is structure-only and validated. | `lib/pipeline_runner.py`, `lib/scene_contract_builder.py` | structure-only scene source | direct scene contract handoff to downstream builders without compatibility translation | M2-T02, M2-T03 | Medium | High |
| M2-T05 | 5 | Validate image builder consumes only canonical scene fields (`scene_id`, timing/objective/script refs context) and style config; no legacy raw fields. | `lib/image_builder.py` | canonical `scene_output` + style configuration | `image_output.images[]` only | M2-T04 | Medium | Medium |
| M2-T06 | 6 | Validate motion builder consumes only canonical image contract fields. | `lib/motion_builder.py` | canonical `image_output` | `motion_output.motions[]` only | M2-T05 | Low | Medium |
| M2-T07 | 7 | Align artifact manifest and stage path handling to canonical contracts only; preserve backward cache compatibility window. | `lib/pipeline_runner.py`, `lib/validation_runner.py` | stage outputs in canonical filenames | manifest and validation all-stage pass with `scenes/image/motion` | M2-T04, M2-T05, M2-T06 | Medium | Medium |
| M2-T08 | 8 | Add/refresh unit and integration validations for contamination prevention (scene must fail if image/motion fields leak). | `lib/schema_validator.py`, `lib/validation_runner.py`, tests | synthetic valid/invalid payloads | automated failing tests on boundary violations | M2-T01..T07 | Medium | High |
| M2-T09 | 9 | Document completion, risk decisions, and rollback notes for bridge removal. | `docs/IMPLEMENTATION_BLUEPRINT.md`, `spec/RELEASE_NOTES.md`, `spec/ADR.md` | execution results and metrics | signed-off milestone closure package | M2-T08 | Low | Low |

---

## Deterministic Sequence Rules
1. Do not execute T04 before T02 and T03 pass.
2. If any contract violation appears in T05/T06, rollback to last passing commit and reopen T02 assumptions.
3. T08 must pass before milestone closure (T09).
4. No deprecated or secondary docs may redefine canonical rules during milestone execution.

---

## Updated Prompt Instructions (for next coding execution)

### Prompt A — Source Scene Refactor (T02/T03)
```text
Refactor scene source generation to output structure-only scene contract fields:
- scene_id, objective, script_refs, start_sec, end_sec, transition_note, schema_version
Remove all image/motion-owned fields from source scene output.
Keep canonical pipeline order unchanged.
Preserve backward compatibility for cached artifacts during migration window.
Run schema and forbidden-field validations after changes.
```

### Prompt B — Bridge Removal (T04)
```text
Remove compatibility bridge adaptation in orchestrator only after source scene generation is structure-only and validated.
Ensure orchestrator directly passes canonical scene contract to image and motion builders.
Do not reintroduce legacy visual/camera/style fields into scene output.
```

### Prompt C — Downstream Contract Tightening (T05/T06/T07)
```text
Update image_builder and motion_builder to consume only canonical contracts.
Image consumes canonical scene contract + style config.
Motion consumes canonical image contract.
Align runtime artifact paths and manifest to canonical scene/image/motion contracts.
```

### Prompt D — Validation & Gate Hardening (T08)
```text
Add/update tests and validations to fail on upstream contamination:
- scene output containing image/motion fields
- image output containing motion-only fields
- motion output containing scene/script/static composition fields
Run full validation checklist and report pass/fail by stage.
```

---

## Canonical Contract & Guard References
- Canonical pipeline and stage ownership: `spec/SYSTEM_ARCH.md`, `spec/AGENT_ARCHITECTURE.md`
- Interface contracts: `spec/SCHEMAS.md`, `spec/schemas/*.schema.json`
- Regeneration scope matrix: `spec/EVOLUTION_CONTRACT.md`
- Contract drift checklist: `spec/VALIDATION_PLAN.md`
- Deprecated normative rule ban: `spec/SPEC_INDEX.md`

---

## Validation Checklist (Milestone 2 completion gate)
- [ ] Scene source emits only structure-only keys (no visual/camera/style/motion fields).
- [ ] Image builder input relies only on canonical scene contract and style config.
- [ ] Motion builder input relies only on canonical image contract.
- [ ] `_separate_scene_image_motion_contracts` (or equivalent bridge code) is removed/deprecated with no runtime dependency.
- [ ] `validation_runner` all-stage checks pass for `scenes`, `image`, `motion`.
- [ ] Forbidden-field checks fail correctly on contaminated payloads.
- [ ] Regeneration behavior follows matrix without over-regeneration.
- [ ] Manifest and artifact paths remain deterministic and canonical.
- [ ] No deprecated docs reintroduce normative rules.

---

## Self-Evolving OS Notes (Post-M2)
- Introduce stage-scoped ownership tests in CI to prevent contract drift regressions.
- Add contract version pinning per run for deterministic replay audits.
- Add stage-level failure isolation dashboards (scene/image/motion split observability).
