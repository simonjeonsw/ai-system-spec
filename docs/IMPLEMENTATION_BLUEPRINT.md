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

## This was not asked, but is important because...
현재 `pipeline_runner` 내부에 scene/image/motion 변환이 함께 존재하면, 장기적으로 “계약은 분리됐지만 코드 책임은 결합된(monolithic orchestrator)” 상태가 됩니다.

이걸 그대로 두면 10x 규모에서 생기는 문제:
- 변경 영향 분석 난이도 급상승
- stage별 장애 격리 실패
- 테스트 피라미드 붕괴(통합테스트 편중)

즉, 다음 마일스톤에서 **모듈 경계 분리(파일 단위)**를 반드시 하셔야 self-evolving OS의 유지비가 선형으로 유지됩니다.

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


## M2 Operational Execution Status (Latest)
- [x] Scene source generation emits structure-only scene fields at source builder level (`lib/scene_source_builder.py`).
- [x] Orchestrator uses direct canonical handoff Scene → Image → Motion without active bridge adapter in runtime path.
- [x] Image builder consumes canonical `scene_output` contract.
- [x] Motion builder consumes canonical `image_output` contract.
- [x] Added automated unit checks for structure-only scene enforcement and image/motion schema compliance (`tests/test_contract_builders.py`).
- [x] Forbidden-field validator remains active as a hard gate (`lib/schema_validator.py`).

### Legacy Bridge Note
Legacy reference module removed: `lib/scene_contract_builder.py` has been deleted from repository. CI guard script now blocks any reintroduction of legacy bridge symbols.


## CI Contract Gates (Stabilization)
- Workflow: `.github/workflows/contract-gates.yml`
- Guard script: `scripts/contract_ci_checks.py`
- Enforced checks:
  - legacy bridge file absence
  - banned legacy symbols not present in Python source
  - canonical handoff symbols present in orchestrator
  - syntax compile + contract unit tests

## M3 Rollout Plan — Metadata SEO/GEO v1.1

### Phase A (0-10 published videos) — GEO-ready interface reservation
- Schema target: `metadata_output.schema.json` v1.1
- Hard gate: SEO fields remain strict (`title`, `description`, `tags`, `chapters`, variants, runtime fields).
- Warn-only GEO placeholders: `target_locale`, `target_region`, `primary_keyword`, `secondary_keywords`.
- Deferred fields (do not generate in Phase A): `faq_snippets`, `key_claims_for_ai`, `canonical_source_urls`.

### Phase B (10-30 published videos) — Partial GEO activation
- Introduce `faq_snippets` and `key_claims_for_ai` behind selective fail rules.
- Enforce `source_ids` linkage to research/source contracts for activated records.
- Continue soft rollout by cohort/channel segment until KPI stability is confirmed.

### Phase C (30-50+ published videos) — Full GEO enforcement
- Add `canonical_source_urls` and strict claim-evidence integrity checks.
- GEO contract violations become hard CI fail conditions.
- Require locale/region completeness and evidence traceability for production publish.

### KPI Triggers for Phase Transition
- Phase A → B: at least 10 published videos, stable metadata generation success rate, and non-trivial GEO placeholder coverage trend.
- Phase B → C: at least 30 published videos, evidence linkage pass rate meets release threshold, and no sustained GEO regression alerts.

### GEO Readiness Logging (Phase A)
- Validation emits warning-only GEO readiness signals for missing locale/region.
- Warning counts are tracked as metrics to support phase transition decisions.


### M3 Governance Completion
- ADR record: `spec/ADR.md` (`ADR-2026-001`).
- Release tracking: `spec/RELEASE_NOTES.md` (`v1.1.0-m3`).
- Regeneration contract linkage: `spec/EVOLUTION_CONTRACT.md` metadata-row policy.


## M3.5 Policy-Driven Autonomy Upgrade

### Deterministic Policy Assets
- Config: `config/geo_phase_policy.json`
- Evaluator: `lib/policy_engine.py`
- CLI report: `scripts/phase_state_report.py`
- Input schema/sample: `spec/schemas/phase_state_input.schema.json`, `spec/samples/phase_state_input_sample.json`

### Autonomous Decision Contract
- GEO escalation and incident/hold outcomes are machine-evaluated.
- Phase A → B promotion is a deterministic state transition, not free-form human judgment.
- Human approval is allowed only after machine criteria already pass.

### Phase B/C Preparation (Locked Drafts)
- Draft-only schemas are added and not active:
  - `metadata_output.phase_b.draft.schema.json`
  - `metadata_output.phase_c.draft.schema.json`
- Source evidence is first-class via `spec/SOURCE_EVIDENCE_CONTRACT.md` and `source_evidence_contract.schema.json`.


## M4 — Decision Enforcement & Accountability
- Decision outputs are binding: each reason code maps to mandatory action or explicit signed override.
- Unknown reason codes fail the decision path.
- Override records are TTL-bounded and auditable.
- Decision provenance includes policy version, evaluated timestamp, input snapshot, and decision hash.
- Weekly calibration reports false-hold / false-promote rates to prevent policy drift.
- GEO Phase B/C fields remain draft-only and inactive during M4.
