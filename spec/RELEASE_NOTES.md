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
