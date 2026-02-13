# Executive Reporting

Executive reports summarize performance, risks, and decisions for stakeholders.

## Weekly Executive Summary Template
**Period:** YYYY-MM-DD → YYYY-MM-DD

**KPI Deltas**
- CTR: <value> (Δ week-over-week)
- AVD: <value> (Δ week-over-week)
- RPM/CPM: <value> (Δ week-over-week)
- Publish cadence: <value>
- geo_readiness_warning_count: <value> (metadata Phase A readiness trend)

**Top Wins**
- Best-performing title/thumbnail experiments (reference metadata_experiments).
- Highest retention episode and key driver.

**Top Risks**
- Failures or SLO breaches (reference pipeline_runs).
- Emerging content or compliance risks.

**Decisions & Actions**
- Decision: <keep/iterate/rollback>
- Owner: <name>
- Due date: <date>

**Notes**
- Link to run logs and experiment logs for evidence.

## Trend Rules
- Two consecutive weeks of CTR decline → open investigation ticket.
- AVD decline > 10% week-over-week → script pacing review.
- Retention drop at 30s for 2 weeks → hook rewrite and scene audit.

## Decision Rubric
- Investigate: KPI declines exceed trend rules or SLO breach observed.
- Iterate: KPIs are flat but within thresholds; test packaging variants.
- Rollback: KPI declines persist after two iterations.


## Metadata GEO Rollout Observation
- Track `geo_readiness_warning_count` by publish batch and week.
- Phase A → B readiness requires sustained warning decline and stable metadata success rates.
- Sudden warning spikes indicate locale/region population regressions and should open a metadata contract incident.


## Deterministic GEO Escalation Policy
- Policy config authority: `config/geo_phase_policy.json`.
- Evaluator authority: `lib/policy_engine.py`.
- Weekly escalation levels are machine-evaluated (green/yellow/red) using `geo_readiness_warning_count` thresholds and sustained increase streak rules.
- Incident creation and phase hold decisions are automatic outputs, not analyst discretion.

## Unified Operational Dashboard Contract
Dashboard must include these required panels:
1. `phase_state`
2. `phase_hold_reason_codes`
3. `ctr_trend`
4. `avd_trend`
5. `metadata_experiment_success_rate`
6. `geo_readiness_warning_count`
7. `source_linkage_pass_rate`

The dashboard must answer exactly:
- "Why can/can't the system promote to Phase B right now?"

Reference implementation command:
- `python scripts/phase_state_report.py spec/samples/phase_state_input_sample.json`


## M4 Accountability Dashboard Additions
- Required integrity panels: `decision_without_action_rate`, `promotion_during_hold_count`, `override_audit_violations`.
- Required calibration panels: `false_hold_rate`, `false_promote_rate` (weekly and monthly).
- Every blocked promotion must include machine reason codes and human-readable explanation text.

- Additional integrity KPIs: `decision_action_closure_rate`, `out_of_band_action_count`, `provenance_linkage_coverage`.
- Promotion operations must be linked to `decision_hash`; unlinked operations are governance incidents.
