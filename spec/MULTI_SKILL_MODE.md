# Multi-Skill Execution Mode

## Purpose
Provide an optional execution mode where a single agent can perform multiple stages in one run
to improve speed and reduce overhead during early phases or low-risk iterations.

## When to Use
- Phase 0 validation runs with small scope.
- Rapid prototyping where latency is more important than strict modularity.
- Low-risk topic exploration where rework cost is minimal.

## When NOT to Use
- Production publishing runs.
- Any run that requires strict QA gates or regulatory review.
- Multi-channel scaling where per-stage observability is required.

## Mode Types
### Mode A: Planner + Research (Fast-Plan)
Combine topic scoring and research into a single execution step.

### Mode B: Research + Scene Builder (Fast-Structure)
Generate research and immediately structure it into scenes.

### Mode C: Planner + Research + Scene Builder (Fast-Prep)
One-shot preparation for scripting, used only for drafts and internal reviews.

## Guardrails
- All outputs must still match the JSON schemas in `spec/SCHEMAS.md`.
- The run must emit `pipeline_runs` entries for each logical stage, even if executed together.
- QA gates from `spec/EVAL.md` must be applied before publish actions.
- Use only approved Gemini models and minimal output settings.

## Required Outputs
Every combined run must still produce:
- PlannerOutput (if Planner is included)
- ResearchOutput (if Research is included)
- SceneOutput (if Scene Builder is included)

## Logging Requirements
For combined execution, emit logs with:
- `stage`: planner | research | scene_builder
- `status`: success | failure
- `input_refs` and `output_refs`

## Default Policy
- Default is modular multi-agent execution.
- Multi-skill execution is an opt-in mode and must be explicitly selected per run.
