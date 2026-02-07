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
