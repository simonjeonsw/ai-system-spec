# Architecture Decision Records (ADR)

## Purpose
Document why key architectural decisions were made, the alternatives considered, and the conditions for revisiting them.

## ADR Template
**Title:**  
**Date:**  
**Status:** Proposed | Accepted | Deprecated  

**Context**
- What problem are we solving?
- What constraints exist (cost, time, tools)?

**Decision**
- What is the decision?

**Alternatives Considered**
- Option A:
- Option B:

**Consequences**
- Benefits:
- Risks:
- Cost impact:

**Revisit Criteria**
- What signal or KPI would trigger a re-evaluation?

## Release Governance Rule
- Every minor/major release must reference at least one ADR ID.

---

## ADR-2026-001 — Metadata Contract v1.1 (SEO hard gate + GEO Phase A warn-only)
**Date:** 2026-02-13  
**Status:** Accepted

**Context**
- M2 locked canonical Scene → Image → Motion boundaries and CI contract checks.
- M3 requires metadata schema evolution for GEO readiness without destabilizing current operations.
- Current channel scale is early-stage; strict GEO enforcement would cause noise and false failures.

**Decision**
- Upgrade metadata schema from 1.0 to 1.1.
- Keep SEO-required fields as hard validation gates.
- Add GEO Phase A placeholders (`target_locale`, `target_region`, `primary_keyword`, `secondary_keywords`) as optional with warning-only readiness checks.
- Defer Phase B/C fields (`faq_snippets`, `key_claims_for_ai`, `canonical_source_urls`) until KPI and volume triggers are met.
- Enforce schema strictness using `additionalProperties: false` to prevent undeclared metadata contract drift.

**Alternatives Considered**
- Option A: Full GEO strict enforcement in M3 Phase A.
  - Rejected due to insufficient evidence inventory and high false-fail risk.
- Option B: No GEO fields until later phases.
  - Rejected because interface reservation is needed to avoid future disruptive schema churn.

**Consequences**
- Benefits:
  - Preserves deterministic metadata contract while enabling phased GEO rollout.
  - Prevents undeclared field pollution before Phase B/C.
  - Keeps CI and local validation consistent via logging/environment decoupling in validation path.
- Risks:
  - Warning-only policy may delay strict GEO data quality improvements.
- Cost impact:
  - Low-to-medium implementation cost; reduced migration risk in later phases.

**Revisit Criteria**
- Move to Phase B when:
  - published videos ≥ 10,
  - metadata generation stability is sustained,
  - `geo_readiness_warning_count` trend improves.
- Move to Phase C when:
  - published videos ≥ 30,
  - evidence-link validation pass rates meet release threshold,
  - no sustained GEO regression alerts.

**Contract Governance Linkage**
- Regeneration policy follows `spec/EVOLUTION_CONTRACT.md` (metadata changes require metadata + validate regeneration).
- Release linkage: `spec/RELEASE_NOTES.md` section `v1.1.0-m3`.

## ADR-2026-002 — Policy-Driven Phase-State Contract (M3.5)
**Date:** 2026-02-13  
**Status:** Accepted

**Context**
- M3 Phase A has observability but promotion decisions can still drift without deterministic policy contracts.
- GEO readiness escalation must be automatic and auditable.
- Phase B/C are not yet activated and must remain draft-locked.

**Decision**
- Introduce machine-evaluable policy config `config/geo_phase_policy.json`.
- Introduce deterministic evaluator `lib/policy_engine.py` and report script `scripts/phase_state_report.py`.
- Define explicit Phase A → B thresholds for videos, CTR/AVD stability, and source-evidence readiness.
- Auto-hold promotion on red GEO escalation or open incident.
- Add first-class source-evidence contract independent of metadata.
- Add locked Phase B/C metadata schema drafts without activation.

**Alternatives Considered**
- Option A: Keep policy as prose in docs only.
  - Rejected due to non-auditable human interpretation drift.
- Option B: Activate Phase B gates immediately.
  - Rejected because this release is policy hardening, not feature activation.

**Consequences**
- Benefits:
  - Promotion decisions become reproducible and explainable.
  - Incident escalation and phase hold are autonomous outputs.
  - Source evidence becomes a prerequisite contract before GEO hard gates.
- Risks:
  - Incorrect threshold tuning can over-hold promotions early.
- Cost impact:
  - Medium; adds policy and evaluation layer plus contract drafts.

**Revisit Criteria**
- Revisit thresholds after 4 weekly windows of data.
- Revisit policy if false-hold rate exceeds operational tolerance.

**Contract Governance Linkage**
- Validation linkage: `spec/VALIDATION_PLAN.md` phase-state validation gate.
- Reporting linkage: `spec/REPORTING.md` unified dashboard contract.
- Release linkage: `spec/RELEASE_NOTES.md` section `v1.1.1-m3.5`.
