# Release Notes

## Release Template
**Release:** vX.Y.Z  
**Date:** YYYY-MM-DD  
**Scope:** (specs/prompts/code)

## Changes
- Summary of updates

## Risks
- Known risks or mitigations

## Rollback Plan
- Steps to revert

## ADR References
- ADR-XXXX

---

## Release: v1.1.0-m3
**Date:** 2026-02-13  
**Scope:** specs + prompts + code + CI

### Changes
- Added metadata contract `spec/schemas/metadata_output.schema.json` v1.1 with:
  - existing SEO fields preserved,
  - GEO Phase A placeholders (`target_locale`, `target_region`, `primary_keyword`, `secondary_keywords`),
  - `additionalProperties: false` for schema hardening.
- Updated `lib/metadata_generator.py` prompt and default schema version to emit JSON-only metadata aligned with v1.1.
- Updated `lib/validation_runner.py` with:
  - metadata stage validation mapping,
  - GEO readiness warning-only checks,
  - logging fallback to keep validation deterministic across CI/local/agent environments,
  - `geo_readiness_warning_count` metric output.
- Added metadata contract tests (`tests/test_metadata_contracts.py`) including undeclared-field rejection.
- Updated CI checks (`.github/workflows/contract-gates.yml`, `scripts/contract_ci_checks.py`) to include metadata-stage validations.
- Updated rollout/spec documents (`docs/IMPLEMENTATION_BLUEPRINT.md`, `spec/SCHEMAS.md`, `spec/VALIDATION_PLAN.md`, `spec/REPORTING.md`).

### Risks
- GEO remains warning-only in Phase A, so data completeness improvements may be slower until Phase B gates activate.
- `additionalProperties: false` may expose hidden producer drift immediately; this is intentional hardening.

### Rollback Plan
1. Revert commit `v1.1.0-m3`.
2. Restore prior metadata schema version and validation mapping.
3. Re-run contract CI and unit tests to verify rollback state.

### ADR References
- ADR-2026-001

### Evolution Contract Linkage
- Regeneration behavior follows `spec/EVOLUTION_CONTRACT.md`:
  - metadata contract changes require regeneration for `metadata` and `validate` stages only.

## Release: v1.1.1-m3.5
**Date:** 2026-02-13  
**Scope:** policy + governance + schema drafts + tooling

### Changes
- Added deterministic policy config: `config/geo_phase_policy.json`.
- Added machine-evaluable phase-state engine: `lib/policy_engine.py`.
- Added phase-state report CLI: `scripts/phase_state_report.py`.
- Added source-evidence first-class schema and spec:
  - `spec/schemas/source_evidence_contract.schema.json`
  - `spec/SOURCE_EVIDENCE_CONTRACT.md`
- Added phase-state input contract artifacts:
  - `spec/schemas/phase_state_input.schema.json`
  - `spec/samples/phase_state_input_sample.json`
- Added locked future drafts for Phase B/C GEO fields:
  - `spec/schemas/metadata_output.phase_b.draft.schema.json`
  - `spec/schemas/metadata_output.phase_c.draft.schema.json`
- Updated reporting/validation/blueprint docs for autonomous phase decisions.
- Added policy engine tests: `tests/test_policy_engine.py`.

### Risks
- Threshold calibration may initially be conservative and hold promotions longer.
- Dashboard/report consumers must use reason codes to avoid opaque decisions.

### Rollback Plan
1. Revert this release commit.
2. Remove policy engine and draft schemas.
3. Keep existing M3 Phase A behavior unchanged.

### ADR References
- ADR-2026-001
- ADR-2026-002
