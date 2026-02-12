# /spec/AGENT_APPLY_GUIDE.md
# Agent OS Application Guide (Secondary)

## Status
This file is **Secondary**. Canonical architecture contracts are defined in:
- `spec/SYSTEM_ARCH.md`
- `spec/AGENT_ARCHITECTURE.md`
- `spec/SCHEMAS.md`

## Purpose
Guide incremental application of Agent OS principles to existing projects.

## Mandatory First Step
Before modifications:
1. Read canonical files from `spec/SPEC_INDEX.md`.
2. Detect mixed responsibilities and boundary violations.
3. Produce structural proposal before behavior changes.

## Canonical Workflow Reference
Do not redefine stage order here.
Use `spec/SYSTEM_ARCH.md` → Canonical Pipeline Contract v1.

## Agent Boundary Reference
Do not redefine boundary rules here.
Use `spec/AGENT_ARCHITECTURE.md` and `spec/SCHEMAS.md`.

## Diff/Test Discipline
- Structural changes require explicit diff traceability.
- Contract changes require ADR linkage.
