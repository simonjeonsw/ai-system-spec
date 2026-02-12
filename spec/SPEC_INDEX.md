# Spec Index

## Purpose
This index defines document authority, ownership, and lifecycle status for all specification files.

## Authority Rules
1. Canonical files define normative rules.
2. Secondary files provide context and implementation guidance only.
3. Deprecated files must not contain normative rules.
4. If conflicts exist, resolve by layer priority: L2 contract files override narrative descriptions in L1/L3.

## Layer Model (L0-L3)
- **L0 Business Intent:** Vision, goals, revenue/retention outcomes.
- **L1 Architecture Contracts:** Pipeline order, stage boundaries, agent responsibilities.
- **L2 Interface Contracts:** JSON/DB schemas, field constraints, compatibility.
- **L3 Operations & Governance:** Validation, runbooks, security, reporting, handoff, release control.

## Canonical Files Registry
| File | Layer | Owner | Review Cadence |
| --- | --- | --- | --- |
| spec/PRD.md | L0 | CTO | Quarterly |
| spec/ROADMAP.md | L0 | CTO | Quarterly |
| docs/STRATEGY.md | L0 | Strategy/Ops | Monthly |
| spec/SYSTEM_ARCH.md | L1 | Architecture | Monthly |
| spec/AGENT_ARCHITECTURE.md | L1 | Architecture | Monthly |
| spec/SCHEMAS.md | L2 | Architecture + QA | Monthly |
| spec/schemas/*.schema.json | L2 | Architecture + QA | Monthly |
| spec/SCHEMA.md | L2 | Data Platform | Monthly |
| spec/schema.sql | L2 | Data Platform | Monthly |
| spec/VALIDATION_PLAN.md | L3 | QA | Monthly |
| spec/OPERATIONS.md | L3 | Ops | Monthly |
| spec/SECURITY.md | L3 | Security/Ops | Quarterly |
| spec/REPORTING.md | L3 | Ops | Monthly |
| spec/HANDOFF.md | L3 | Ops | Per handoff |
| spec/ADR.md | L3 | Architecture | Per change |
| spec/RELEASE_NOTES.md | L3 | Release Manager | Per release |
| spec/EVOLUTION_CONTRACT.md | L3 | Architecture + QA | Monthly |

## Secondary Files Registry
| File | Layer | Reason |
| --- | --- | --- |
| spec/PRODUCT_SPEC.md | L0 | Product-level elaboration and examples |
| spec/TECH_SPEC.md | L1/L2 | Implementation detail and vocabulary |
| spec/IMPLEMENTATION_PLAN.md | L3 | Historical implementation planning context |
| spec/CURRENT_STATE.md | L3 | Point-in-time status assessment |
| spec/MULTI_SKILL_MODE.md | L1 | Optional execution mode guidance |

## Deprecated Files Registry (Phase D1)
| File | Layer | Canonical Replacement |
| --- | --- | --- |
| spec/AGENTS.md | L1 | spec/AGENT_ARCHITECTURE.md, spec/AGENT_RULES.md |
| spec/STRUCTURE_DESIGN_SPEC.md | L1/L2 | spec/AGENT_ARCHITECTURE.md, spec/SCHEMAS.md |

## Deprecation Policy
- Deprecated files are retained for traceability for at least 2 release cycles.
- Deprecated files must include a top deprecation banner and replacement links.
- Deprecated files must not add normative requirements.
- Any normative statement found in deprecated files is a **contract error**.

## Deprecation Timeline
- **R0 (now):** Canonical map + deprecation banners + rule-ban enabled.
- **R1:** Secondary docs converted to reference style, duplicates removed.
- **R2:** Deprecated docs reduced to migration stubs only.

## Contract Drift Controls
- Pre-release `Contract Drift Checklist` is mandatory (see `spec/VALIDATION_PLAN.md`).
- `Regeneration Scope Matrix` is mandatory for stage-change impact (see `spec/EVOLUTION_CONTRACT.md`).
