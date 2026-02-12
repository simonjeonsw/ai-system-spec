# /spec/AGENT_APPLY_GUIDE.md
# Agent OS Application Guide

## Purpose
This document instructs agents how to apply Agent OS to an existing project.

The project already exists.
Do NOT redesign it from scratch.
Your task is to refactor and align it incrementally.

---

## Mandatory First Step: Spec Refactoring

Before generating or modifying any content:

1. Read the current project repository spec.
2. Identify:
   - Mixed responsibilities
   - Implicit assumptions
   - Missing structure boundaries
3. Produce a **Spec Refactor Proposal**:
   - No content generation
   - No behavior changes
   - Structure only

If this step is skipped, ALL subsequent outputs are invalid.

---

## Spec Refactor Rules

- Preserve original intent
- Split responsibilities, do not merge
- Prefer adding sections over deleting content
- Use diffs only

---

## Canonical Workflow

All agents MUST follow this order:

research → plan → script → scene → image → motion → metadata → validate

Skipping or reordering steps is forbidden unless explicitly approved.

---

## Agent Boundaries (Hard Rules)

- Script agent cannot decide scenes
- Scene agent cannot generate images
- Image agent cannot modify text
- Motion agent cannot invent visuals

Violations must be reported, not corrected silently.

---

## Diff and Test Discipline

- All changes must be expressed as unified diffs
- Structural changes require tests
- If tests are missing, generate them

---

## Failure Handling

If an agent fails:
1. Retry within assigned boundary
2. Apply fallback
3. Log failure and continue

Never restart the entire pipeline.

---

## Success Criteria

The system is considered successful if:
- Project structure becomes clearer
- Responsibility boundaries are enforced
- Regeneration scope is reduced
