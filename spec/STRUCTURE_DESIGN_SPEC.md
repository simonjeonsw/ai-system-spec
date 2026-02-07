# Structure Design Specification

## Purpose
Define the role that converts Research/Planner outputs into a **scene/beat-level structure**. This stage designs the rhythm and flow of the content and provides a **structural blueprint** for the next stages (Script/Visual/Voice).

## Inputs
- Summary of Planner/Research outputs (key facts, thesis, evidence, insights)
- Target metrics (retention, revenue, etc.)

## Outputs
- Scene list (with timecodes)
  - Hook / Proof / Insight / Payoff mapping
- Per-scene purpose (why the scene exists)
- Per-scene CTA (Call To Action)
- Visual and voice hints

## Responsibilities
- **Core role**: Break research results into viewer-experience units (scenes/beats) and design a structure that drives engagement, persuasion, and conversion.
- **Includes**
  - Flow/rhythm design (pacing, tension, release)
  - Placement aligned to Hook/Proof/Insight/Payoff
  - CTA placement and intensity
  - Hints that improve downstream understanding for Visual/Voice stages
- **Excludes**
  - Writing the actual script lines/dialogue
  - Visual production details (thumbnail/graphics/shooting specifics)
  - Concrete voice performance/recording direction

## Boundaries and Handoff Rules
- **Script stage**
  - Handoff: scene purposes, logical transitions, key messages/evidence, CTA placement
  - Script keeps the scene units but expands into concrete lines/dialogue and narrative.
- **Visual stage**
  - Handoff: per-scene visual hints (charts/data/visual metaphors), transition points
  - Visual expands hints into concrete assets and staging.
- **Voice stage**
  - Handoff: per-scene voice hints (pace, emphasis, emotional tone, breathing)
  - Voice designs the actual delivery tone aligned to intent.
- **Prohibited**
  - Do not preempt Script/Visual/Voice with their final deliverables (finished lines, layout, recording direction).

## Quality Criteria
- Structural decisions must tie directly to target metrics (retention/revenue).
- Each scene must clearly state “purpose-evidence-CTA.”
- The balance and order of Hook/Proof/Insight/Payoff must be explicit.
- Transitions between scenes must remain logically connected.

## Required Output Schema
```yaml
structure_design:
  input_summary:
    planner_research_summary: "<summary text>"
    target_metrics: ["retention", "revenue"]
  scenes:
    - id: 1
      timecode: "00:00-00:20"
      beat_type: "Hook" # Hook | Proof | Insight | Payoff
      purpose: "<scene purpose>"
      key_points:
        - "<key point>"
      cta: "<scene CTA>"
      visual_hints:
        - "<visual hint>"
      voice_hints:
        - "<voice hint>"
      handoff_notes:
        script: "<handoff notes for script stage>"
        visual: "<handoff notes for visual stage>"
        voice: "<handoff notes for voice stage>"
```
