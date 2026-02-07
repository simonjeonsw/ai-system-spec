# Implementation Plan

This document defines module-level interfaces before any code is written.

## Module Interfaces

### Planner
**Input**
- Benchmarking → Planner input format (PRODUCT_SPEC).
- Channel configuration (tone, format, KPI targets).
**Output**
- Topic shortlist with scores and selected topic (prompts/planner.md).
**Implementation targets**
- Module: `src/planner/`
- Functions: `score_topics()`, `select_topic()`, `emit_planner_brief()`

### Research
**Input**
- Planner brief with selected topic and topic_candidates context.
**Output**
- Research Output Format (PRODUCT_SPEC).
**Implementation targets**
- Module: `src/research/`
- Functions: `run_research()`, `validate_sources()`, `emit_research_output()`

### Scene Builder
**Input**
- Research output (PRODUCT_SPEC).
**Output**
- Scene Structuring Spec (TECH_SPEC).
**Implementation targets**
- Module: `src/scene_builder/`
- Functions: `build_scenes()`, `map_sources()`, `validate_scene_schema()`

### Script
**Input**
- Scene outputs with source_refs and evidence_sources.
**Output**
- Script draft with citations embedded.
**Implementation targets**
- Module: `src/script/`
- Functions: `draft_script()`, `apply_narrative_rules()`

### QA
**Input**
- Script draft and scene outputs.
**Output**
- QA pass/fail summary with rewrite triggers.
**Implementation targets**
- Module: `src/qa/`
- Functions: `run_checklists()`, `emit_qc_report()`

### Ops
**Input**
- Final script, visual assets, metadata experiments.
**Output**
- Publish status and metadata_experiments logs.
**Implementation targets**
- Module: `src/ops/`
- Functions: `publish_video()`, `log_experiment()`, `emit_run_log()`

## Exit Criteria (Ready for Code)
- KPI thresholds and rewrite triggers are defined (EVAL.md).
- Run-log emission policy is defined (OPERATIONS.md).
- Validation plan is finalized (VALIDATION_PLAN.md).
- Module interfaces above are approved.
