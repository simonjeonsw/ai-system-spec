# MCP + GitHub Context Integration

## Purpose
Inject persistent, canonical project context into agent executions.

## Required Context Files (Canonical)
- spec/SPEC_INDEX.md
- spec/SYSTEM_ARCH.md
- spec/AGENT_ARCHITECTURE.md
- spec/SCHEMAS.md
- spec/VALIDATION_PLAN.md

## Context Policy
- Canonical spec files override all prompts and ad-hoc instructions.
- Deprecated files must not be loaded as normative context.

## Version Discipline
- Spec changes require commit and release-note linkage.
