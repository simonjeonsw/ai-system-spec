# Product Specification

## Product Goal
Build a fully automated system to generate,
evaluate, and scale finance & economics content
optimized for retention and monetization.

## Core Capabilities (MVP)
- Topic planning
- Market & data research
- Content logic generation
- Quality evaluation
- Version-controlled outputs

## Out of Scope (MVP)
- Manual creative-heavy editing
- Emotion-driven storytelling
- Trend chasing without ROI logic

## Target Outcomes
- Repeatable high-CPM content
- Predictable production
- Multi-channel scalability

## Research Output Format (English Only)
Research outputs must be structured to support downstream scene generation.

**Required fields**
- `executive_summary` (string)
- `key_facts` (array of strings)
- `key_fact_sources` (array of objects: `{ "claim": "", "source_ids": [""] }`)
- `data_points` (array of objects: `{ "metric": "", "value": "", "timeframe": "", "source_id": "" }`)
- `sources` (array of objects: `{ "source_id": "", "title": "", "url": "", "as_of_date": "", "source_tier": "", "freshness_window_days": 0 }`)
- `contrarian_angle` (string)
- `viewer_takeaway` (string)

**Template**
```json
{
  "executive_summary": "...",
  "key_facts": ["...", "..."],
  "key_fact_sources": [
    { "claim": "...", "source_ids": ["src-001"] }
  ],
  "data_points": [
    { "metric": "...", "value": "...", "timeframe": "...", "source_id": "src-001" }
  ],
  "sources": [
    {
      "source_id": "src-001",
      "title": "...",
      "url": "https://example.com/source-1",
      "as_of_date": "2024-06-01",
      "source_tier": "tier_1",
      "freshness_window_days": 180
    }
  ],
  "contrarian_angle": "...",
  "viewer_takeaway": "..."
}
```

**Rules**
- Every key_fact must have a corresponding key_fact_sources entry.
- sources must include source_tier and freshness_window_days.

## Data Governance (Sources)
**Trust tiers**
- `tier_1`: Primary sources (government, central banks, regulators, audited filings)
- `tier_2`: Reputable secondary sources (major financial press, research firms)
- `tier_3`: Other sources (blogs, social, unverified commentary)

**Freshness rules**
- Macro data: max 12 months unless explicitly labeled “historical.”
- Market data: max 30 days unless a longer window is justified.
- Policy/regulatory updates: max 90 days unless superseded.

**Usage rules**
- Tier 3 sources require a Tier 1 or Tier 2 corroboration.
- Any source outside freshness rules must be flagged in risk_flags as `stale_data`.

## Topic Prioritization
Planner must score candidate topics before research begins.

**Scoring rubric (1–5 each)**
- Audience fit (target audience pain + search demand)
- Novelty (non-obvious angle vs. crowded narratives)
- Monetization potential (RPM/CPM likelihood, sponsor suitability)
- Evidence availability (credible, recent sources available)
- Production feasibility (data availability, visualizability, runtime)

**Selection rule**
- Provide a scored shortlist (3–5 topics) and select the top-ranked topic with a brief rationale.

**Benchmarking weighting guidance**
- Strong hook pattern alignment can increase the novelty score.
- Clear packaging patterns (titles/thumbnails) can increase audience fit.
- Proven pacing benchmarks can increase production feasibility.

## Benchmarking Outputs
Competitor intelligence must produce actionable packaging and topic insights.

**Required outputs**
- Top hook patterns by topic cluster.
- Thumbnail text patterns (length, phrasing, motif).
- Pacing benchmarks (scene counts, average segment duration).
- Topic gaps (underserved audience questions).

## Benchmarking → Planner Input Format
Benchmarking outputs must be normalized before they reach the Planner.

**Schema (JSON)**
```json
{
  "top_hooks": ["", ""],
  "packaging_patterns": ["", ""],
  "topic_gaps": ["", ""],
  "pacing_benchmarks": [
    { "avg_scene_count": 0, "avg_scene_duration_sec": 0 }
  ]
}
```

## Revenue / Retention / Automation KPI
Track KPIs by channel type to ensure revenue growth, viewer retention, and automation efficiency.

### Channel-Specific Success Metrics
- Finance / Economics
  - CTR (thumbnail + title)
  - Average View Duration (AVD) and 30-second retention
  - RPM / CPM and total revenue per video
  - Return viewer rate and subscriber conversion
- Education (general)
  - CTR and impression-to-view rate
  - AVD and completion rate
  - Watch time per session and playlist continuation rate
  - RPM and sponsor-read conversion (if applicable)
- News / Analysis
  - CTR and short-term velocity (views in first 24 hours)
  - AVD and retention curve stability
  - RPM / CPM and ad fill rate
  - Returning viewer rate by topic series

### Automation Efficiency Metrics
- Time from idea → published video
- Agent rerun rate (rewrites per episode)
- QA pass rate on first submission
- Cost per produced minute (API + compute)

## Expansion Targets
- Script automation
- Thumbnail automation
- Voice automation
- Upload & metadata automation
