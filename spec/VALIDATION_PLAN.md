# Validation Plan

Validation ensures structured outputs match schemas and quality gates before publish.

## Unit Validation
- Schema validation for planner, research, scene, and script outputs.
- Field-level checks for required keys and types.
- Source governance checks (source_tier, freshness_window_days).
- Validate against JSON Schemas in SCHEMAS.md and `spec/schemas/*.schema.json`.

## Integration Validation
- End-to-end sample run from Planner → Ops using a fixed test topic.
- Verify run logs are emitted at each stage with pipeline_runs references.

## Regression Validation
- Compare outputs against a golden baseline to detect drift.
- Re-run after any prompt or spec change (major/minor release).

## Quality Gate
- Any schema failure blocks publish.
- Any SLO breach triggers a review before release.
- Any uncorroborated Tier 3 claim or stale source without risk_flags blocks publish.
