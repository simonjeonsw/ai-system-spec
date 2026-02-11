# /spec/AGENT_ARCHITECTURE.md

Agent Architecture & Diff-Based Workflow Specification
Purpose

This document defines why, how, and in what structure this project’s agent-based Content OS operates so that it can:

Preserve semantic consistency

Safely evolve through changes

Enforce single-responsibility agents

Apply diff-only generation with automatic validation

This document is a behavioral specification for both humans and AI agents.

1. End-to-End Pipeline Overview
✅ Canonical Pipeline
Research
 → Script
   → Scene
     → Image
       → Motion
         → Metadata
           → Validate


Each stage follows Single Responsibility Principle.
No stage is allowed to modify the meaning of any previous stage.

2. Agent Responsibilities (Strict Definitions)
2.1 Research Agent

Role

Fact gathering

Trend extraction

Reference summarization

Output Rules

Bullet-point facts only

Evidence to support later claims

❌ No narrative or storytelling

2.2 Script Agent (Semantic Source of Truth)

Role

Message

Logic

Emotional trajectory

Rules

Script is the Single Source of Truth

All downstream agents may only reinterpret, never modify it

Example Output

script:
  hook: "AI now writes code faster than humans"
  body:
    - "Speed increased"
    - "Responsibility decreased"
  conclusion: "Tools must not replace judgment"

2.3 Scene Agent (Temporal Structure Only)

Role

Translate Script into time-based structure

Control rhythm and pacing

Strictly Forbidden

Images

Motion

Visual style

Example Output

scene:
  - id: s1
    role: hook
    duration: 3s
    intent: attention
    script_ref: hook


Scene defines when and why, never how it looks.

2.4 Image Agent (Static Visual Composition)

Role

Convert scenes into static visual assets

Ensure visual consistency

Inputs

scene.id

scene.intent

Script summary

Canon (style rules)

Example Output

image:
  s1:
    type: text_overlay
    palette: high_contrast
    elements:
      - large_typography
      - dark_background

2.5 Motion Agent (Direction & Animation)

Role

Animate images

Platform-specific direction

Viewer retention optimization

Why Motion is Separate

Motion is platform-dependent

Images are reusable assets

Example Output

motion:
  s1:
    entrance: scale_in
    emphasis: micro_shake
    exit: hard_cut

2.6 Metadata Agent

Role

Title

Description

Tags

Thumbnail text

Inputs

Script core message

Scene structure

2.7 Validate Agent (Safety Gate)

Role

Structural consistency checks

Rule enforcement

Automated test execution

3. Why Scene Must Not Contain Image or Motion
Problems When Combined

Changes cascade across stages

Scene becomes non-reusable

A/B testing becomes impossible

Benefits After Separation
Component	Benefit
Scene	Structure reuse
Image	Asset reuse
Motion	Rapid experimentation

This architecture elevates video creation to OS-level abstraction.

4. Diff-Based Generation Strategy (Critical)
Core Rule

Agents must never regenerate full outputs
Only minimal diffs are allowed

4.1 Diff Rules

Modify only the smallest required unit

Preserve all unaffected content

Diff must be explicit

Example

scene:
  - id: s2
-   duration: 4s
+   duration: 5s

4.2 Why Diff-Only Matters

Prevents semantic drift

Enables traceability

Reduces hallucination risk

5. Automatic Test Generation
5.1 Test Philosophy

❌ “Is this good?”

✅ “Is anything broken?”

5.2 Generated Test Categories
Scene Tests

Unique scene IDs

Total duration within platform limits

Image Tests

Every scene has a corresponding image

Motion Tests

Platform constraints respected

5.3 Conceptual Test Example
def test_scene_links():
    for scene_id in scene:
        assert scene_id in image
        assert scene_id in motion

6. Execution Order Rules
Hard Constraints

Downstream agents cannot run until upstream output is finalized

Order is always: diff → test → apply

Validation failure triggers rollback

7. Required Agent Reasoning Pattern
Forbidden

“I rewrote this for clarity”

“I regenerated the full output”

Required

Does this step own this responsibility?

Did I preserve upstream meaning?

Is a diff sufficient?

8. Core Philosophy

AI is not the creator
It is a constrained execution module

Meaning ends at Script

Interpretation follows

Experimentation belongs to Motion

9. Summary Rules (Agent Memory)
Script = Meaning
Scene = Time
Image = Static Visual
Motion = Direction
Diff = Safety
Test = Trust

10. Agent Self-Check Checklist

 Did I operate only within my responsibility?

 Did I preserve upstream semantics?

 Did I produce diffs only?

 Did all tests pass?