# Agent Definitions & Responsibilities

## Research Agent
- Collect macro, financial, and market data
- Source-based summaries
- Bias minimization

## Script Agent
- Retention-optimized narrative
- Hook → Proof → Insight → Payoff structure

## Visual Agent
- High-CTR thumbnail strategy
- Information-dense but simple visuals
- Thumbnail A/B test planning and variant tracking

## Voice Agent
- Clear, authoritative delivery style
- Information-first tone

## QA Agent
- Fact verification
- Logical consistency
- Viewer perspective validation
### QA Checklist (by stage)
**Research output**
- Are sources clear (original links, data as-of date, scope)?
- Can facts be verified (numbers, definitions, comparison baselines)?
- Are bias/conflicts of interest disclosed?
**Script draft**
- Is the claim → evidence → interpretation flow logically connected?
- Is evidence complete and not exaggerated for each key claim?
- From the viewer perspective, is the question resolved or next action clear?
**Final**
- Is message consistency preserved (no distortion/exaggeration vs draft)?
- Are terms, numbers, and citations accurate?
- Are ambiguous or overly definitive statements removed to prevent confusion?
### Failure criteria
- Includes unverifiable facts or unclear sources.
- Logical leaps (conclusions without evidence, conflicting claims).
- Core viewer questions remain unanswered.
### Rewrite triggers
- Two or more checklist items fail.
- One or more factual errors found.
- Missing bias/conflict disclosure that could undermine trust.

## Ops Agent
- Upload execution (final file validation, platform ingest, and publish confirmation)
- Scheduling (release calendar alignment, timezone checks, and contingency rescheduling)
- Metadata optimization (titles, descriptions, tags, chapters, and pinned comment setup)
- Thumbnail operations (asset handoff, version tracking, and A/B test coordination)
- Log metadata experiment outcomes using the metadata_experiments schema
