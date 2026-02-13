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
