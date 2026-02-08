# AI-Native Finance Content System

## Overview
This repository defines an AI-native, agent-based content production system
for high-CPM finance & economics YouTube channels.

The system is designed to:
- Maximize retention and monetization
- Minimize manual work
- Enable multi-channel scaling
- Enforce spec-driven execution

This is not a prompt collection.
This is an operating system for an AI-driven media company.

## Core Principles
- Profit-first
- Automation-first
- Spec-driven agents
- Continuous evaluation and rewrite loops

## Repository Structure
/spec
  PRD.md
  PRODUCT_SPEC.md
  RULES.md
  SYSTEM_ARCH.md
  MULTI_SKILL_MODE.md
  schemas/
  samples/
  AGENTS.md
  AGENT_RULES.md
  STYLE.md
  EVAL.md
  ROADMAP.md
  MAIN_CONTEXT.md
  TECH_SPEC.md

/prompts
  system.md
  planner.md
  research.md
  evaluator.md

/mcp
  mcp_config.md

## Execution Model
Planner
 → Research
 → Script (future)
 → Visual (future)
 → QA / Evaluator
 → Ops (future)

## CLI Usage (Current)
```bash
python -m lib.trend_scout
python -m lib.researcher
python -m lib.planner
python -m lib.scene_builder
python -m lib.scripter
python -m lib.metadata_generator data/planner_<video_id>.json data/script_<video_id>.json
python -m lib.validation_runner all --url <youtube_url_or_id>
python -m lib.analytics_collector <video_id> [start_date] [end_date]
python -m lib.pipeline_runner --url <youtube_url_or_id> --validate
```

### Environment Setup
- Copy `.env.example` to `.env` and populate API keys.
- Each stage writes local backups to `data/<stage>_<video_id>.json`.
- Outputs are upserted to Supabase to avoid duplicate rows on refresh.

## Golden Rule
Spec files override all agent instructions.
All agents must load spec context before execution.
