# AI-Native Finance Content System

## Overview
Spec-driven AI content operating system for finance/economics channels.

## Canonical Pipeline
Refer to `spec/SYSTEM_ARCH.md` → **Canonical Pipeline Contract v1**.

Canonical order:
`research → plan → script → scene → image → motion → metadata → validate`

## Repository Structure
- `/spec`: authoritative specifications and contracts
- `/prompts`: agent prompts
- `/lib`: runtime modules
- `/data`: generated artifacts

## CLI Usage (Current Runtime)
```bash
python -m lib.trend_scout
python -m lib.researcher
python -m lib.planner
python -m lib.scene_builder
python -m lib.scripter
python -m lib.metadata_generator data/planner_<video_id>.json data/script_<video_id>.json
python -m lib.validation_runner all --url <youtube_url_or_id>
python -m lib.pipeline_runner --url <youtube_url_or_id> --validate
```

## Governance
- Spec authority and document status: `spec/SPEC_INDEX.md`
- Contract drift and regeneration scope: `spec/EVOLUTION_CONTRACT.md`
