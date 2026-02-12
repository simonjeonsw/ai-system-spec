# Validation Plan

## Status
Canonical (L3)

Validation ensures structured outputs match schemas and quality gates before release.

## Unit Validation
- Schema validation for planner, research, script, scene, image, and motion outputs.
- Field-level checks for required keys and types.
- Source governance checks where applicable.

## Integration Validation
- End-to-end run must preserve canonical stage dependency order.
- Validate stage artifacts against regeneration scope policy.

## Regression Validation
- Compare outputs against approved baseline contracts.
- Re-run after contract, schema, or deprecation-status changes.

## Contract Drift Checklist (Pre-Release Mandatory)
1. Canonical pipeline order unchanged and referenced, not redefined.
2. Scene output contains structure/timing only.
3. Image output contains static asset contract only.
4. Motion output contains temporal directives only.
5. Deprecated files contain no normative rules.
6. Secondary files contain no conflicting normative statements.
7. Regeneration scope references match `spec/EVOLUTION_CONTRACT.md`.
8. Schema and prose contract versions are aligned.

## Quality Gate
- Any contract drift checklist failure blocks release.
- Any boundary violation blocks release.
- Any deprecated-document normative rule blocks release.
