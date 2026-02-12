# Agent Rules & Governance

## Status
Canonical (L3 governance)

## Global Rules
- Always load canonical specs from `spec/SPEC_INDEX.md`.
- Operate only within assigned stage responsibilities.
- Report uncertainty explicitly.
- Do not bypass validation gate.

## Contract Governance Rules
- No duplicated normative rule across files.
- Canonical rules may only be defined in canonical files.
- Deprecated files must not contain normative rules.
- Violations are contract errors.

## Stage Boundary Rule (Mandatory)
- Scene: structure/timing only.
- Image: static visual assets only.
- Motion: temporal animation only.

## Change Management
- Contract changes require ADR references.
- Release artifacts must pass contract drift checklist.
