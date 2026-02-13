# Main Context Document (MCD)

## Purpose
This document defines system-level context and links to canonical contract sources.

## Success Definition
Ship finance/economics content that improves revenue, retention, and automation efficiency while preserving contract consistency.

## Source of Truth Hierarchy
1. `spec/SPEC_INDEX.md` (authority map)
2. Canonical files listed in `spec/SPEC_INDEX.md`
3. Secondary files (non-normative)
4. Prompts and operational instructions

## L0-L3 Layer Ownership
- **L0:** PRD, ROADMAP, STRATEGY
- **L1:** SYSTEM_ARCH, AGENT_ARCHITECTURE
- **L2:** SCHEMAS + schema files, SCHEMA + schema.sql
- **L3:** VALIDATION_PLAN, OPERATIONS, SECURITY, REPORTING, HANDOFF, ADR, RELEASE_NOTES, EVOLUTION_CONTRACT

## Non-Negotiables
- No undocumented contract changes
- No pipeline order reinterpretation
- No boundary violations across Scene/Image/Motion
- All artifacts and specs in English

## Core References
- Canonical pipeline: `spec/SYSTEM_ARCH.md`
- Boundary contracts: `spec/AGENT_ARCHITECTURE.md`
- Interface contracts: `spec/SCHEMAS.md`
- Regeneration policy: `spec/EVOLUTION_CONTRACT.md`
