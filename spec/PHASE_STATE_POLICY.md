# Phase State Policy (Machine-Evaluable)

## Status
Canonical (L3)

## Purpose
Define deterministic rules for GEO escalation and Phase A → B promotion decisions.

## Policy Source
- Config authority: `config/geo_phase_policy.json`
- Evaluator runtime: `lib/policy_engine.py`
- Report command: `python scripts/phase_state_report.py spec/samples/phase_state_input_sample.json`

## GEO Readiness Escalation
- Metric: `geo_readiness_warning_count`
- Weekly deterministic thresholds:
  - Yellow: warning count >= 3 and sustained increase for 2 weeks.
  - Red: warning count >= 5 and sustained increase for 3 weeks.
- Incident rule:
  - Auto-create incident on yellow or red.
- Hold rule:
  - Auto-hold phase promotion on red.
  - Auto-hold while incident is open.

## Phase A → B Transition Contract
Promotion is allowed only when all conditions pass:
1. Published videos in [10, 30].
2. CTR stability window (4 weeks) passes max relative range <= 0.2.
3. AVD stability window (4 weeks) passes max relative range <= 0.2.
4. Source contract ready is true.
5. Source linkage pass rate >= 0.98.
6. Research source coverage >= 0.95.
7. No open incident.

## Exception Handling
- Insufficient data: hold.
- Incident open: hold.
- Manual override for rule definition is not allowed.

## Rollback Contract (Post-Promotion)
- If enabled rollback triggers breach in 2-week window:
  - CTR drop vs baseline >= 20%, or
  - AVD drop vs baseline >= 20%, or
  - source linkage pass rate < 0.95,
  then action: revert to Phase A.

## Explainability Requirement
The system must always produce machine-readable reason codes for hold/promotion decisions.


## Decision-to-Action Enforcement Contract
- Every policy reason code must map to a mandatory action (see `config/geo_phase_policy.json`).
- Unknown reason codes are contract errors and must fail evaluation.
- Promotion cannot proceed when `phase_hold=true` or `incident_required=true` with unresolved incident state.
- If information is insufficient, emit `decision_hold_pending_info` and block promotion until data sufficiency recovers.

## Signed Override Contract
- Overrides must be explicit, signed, and time-bounded.
- Required fields: actor, approver, justification, created_at, expires_at, signature, scope.
- Overrides exceeding TTL or missing required fields are audit violations and cannot bypass policy.

## Decision Provenance
- Each decision must emit immutable provenance: policy version, input snapshot, evaluated timestamp, and decision hash.
- Decision provenance is required for audit and replay checks.
