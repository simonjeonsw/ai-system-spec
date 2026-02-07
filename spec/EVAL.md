# Evaluation & Feedback Framework

## Automatic Metrics
- 5s hook retention
- 30s retention
- Full video completion rate
- CTR

## Pass Criteria
- Below threshold → auto rewrite

## Human Review (Optional)
- Monetization potential
- Legal & compliance risk

## QA Checklist (by stage: factuality/logic/viewer perspective)
### Research output
- Factuality: Are sources, dates, and scope clearly stated?
- Logic: Are comparison or estimation assumptions explicit?
- Viewer perspective: Is the core question (why it matters/what to do) clear?
### Script draft
- Factuality: Do all numbers and citations match the original sources?
- Logic: Is the claim → evidence → interpretation flow coherent?
- Viewer perspective: Is the question–answer structure clear and easy to follow?
### Final
- Factuality: Is information preserved without distortion/exaggeration vs draft?
- Logic: Does the conclusion align with the evidence?
- Viewer perspective: Are overconfident or overly simplified statements removed?

## Scene-Level QA Checklist
- Factual accuracy per scene (claims match cited sources).
- Claim-evidence alignment (no unsupported leaps).
- Source traceability (each key claim maps to source_refs from research output).
- Logical continuity between scenes (transitions are justified).
- Viewer clarity (scene objective is obvious within 5–10 seconds).
- Retention risk scan (no dead air or redundant scenes).

**Pass criteria**
- Any scene scoring below 3/5 on factual accuracy or claim-evidence alignment fails the review.
- Two or more scenes scoring below 3/5 on viewer clarity triggers a rewrite.

## Research → Scene Alignment Checklist
- Every scene key_claim matches a research key_fact or data_point.
- Every scene source_refs entry resolves to research sources or data_points.source_id.
- Every scene source_refs entry resolves to research sources or data_points.source.
- Any unmatched claim must be flagged in risk_flags.

**Pass criteria**
- Any unmatched claim or missing source mapping fails the review.

## Risk Flags Validation
- All risk_flags values must match the TECH_SPEC risk flag vocabulary.
- Any unknown value fails the review.

## QA Failure criteria
- Includes unverifiable facts or unclear sources.
- Missing evidence for key claims or logical leaps.
- Core viewer question is not resolved.

## QA Rewrite triggers
- Two or more checklist items fail.
- One or more factual errors found.
- Missing bias/conflict disclosure that could undermine trust.

## Structure Design Quality Checklist
- Flow quality
  - Retention curve sustained (no major drop-offs between beats)
  - Pacing keeps momentum (no overlong setup or dense segments)
- Scene purpose clarity
  - Each scene has a single, explicit purpose (hook, proof, insight, payoff)
  - Scene outcomes are stated or implied before transitioning
- Transition logic
  - Transitions connect prior beat to next beat with a clear rationale
  - No abrupt topic jumps or missing connective tissue

## Structure Design Fail/Redo Triggers (QA Agent)
- Fail if retention curve shows a sharp drop tied to a scene transition or mid-scene stall.
- Fail if any scene lacks an explicit purpose or does not advance the narrative.
- Fail if transitions cannot be explained in one sentence by the QA Agent.
- Redo flow: QA Agent flags the specific timestamp/scene → Script Agent rewrites the affected segment(s) → QA Agent rechecks checklist above.

## Retrigger Rules
- Low retention → Script Agent rewrite
- Low CTR → Visual Agent rewrite
