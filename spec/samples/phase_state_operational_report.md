# M4 Decision Enforcement & Accountability — Operational Readiness Report

## 1) Human-readable readiness summary
- **Core policy gate is enforcing hold correctly**: current sample state remains `phase_hold=true`, `incident_required=true`, and promotion is blocked.
- **Decision provenance is generated** with immutable `decision_hash`, policy version, and input snapshot.
- **Override audit control is active**: the sample override is rejected with `OVERRIDE_TTL_EXCEEDS_POLICY`, producing `override_audit_violations=1`.
- **Operational closure is NOT complete**: only 1 of many mandatory actions is executed; closure is false.

## 2) Decision → action → audit closure validation (sample)
- Mandatory actions are emitted deterministically for all reason codes.
- Sample executed action set is incomplete; therefore `decision_action_closure_rate=0.0` and `decision_without_action_rate=1.0`.
- Provenance linkage was tested with mixed external artifacts:
  - linked incident event carries current `decision_hash`
  - unlinked release event does not carry decision hash
  - resulting `provenance_linkage_coverage=0.5`.

## 3) External enforcement gaps / OOB bypass risk
- **Promotion during hold still appears in observed operations** (`promotion_during_hold_count=1`): this proves the hard block is not externally guaranteed.
- **Out-of-band action count is non-zero** (`out_of_band_action_count=1`): release/promotion can bypass decision hash lineage.
- **Missing mandatory actions remain high**: operational orchestrator is not yet enforcing action completion before execution.

## 4) Updated operational KPIs (sample)
- decision_action_closure_rate: `0.0`
- decision_without_action_rate: `1.0`
- promotion_during_hold_count: `1`
- override_audit_violation_rate: `1.0`
- out_of_band_action_count: `1`
- provenance_linkage_coverage: `0.5`
- calibration stale_label_rate: `0.5`
- calibration governance_ok: `false`

## 5) Requires live/simulated verification before full autonomy
1. Enforce release-system preflight check that rejects execution when `phase_hold=true`.
2. Enforce decision hash and/or signed override reference as a required field in incident/release APIs.
3. Enforce override TTL at execution time (not only at decision time) to prevent delayed replay.
4. Add weekly calibration label freshness job and escalation policy when stale labels > 0.

## 6) Immediate first-action execution readiness
- Entry point prepared: `policy_enforcement.check_phase_state(payload)` now returns:
  - policy decision
  - operational enforcement metrics
  - calibration staleness governance block
- This can be wired directly into first-action runbooks and CI gating.
