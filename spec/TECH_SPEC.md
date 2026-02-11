# Technical Specification

## Primary Tools
- GitHub (source of truth)
- Cursor (agent + MCP IDE)
- MCP servers (context + tools)

## Architecture Rules
- Markdown for all specs
- GitHub = canonical storage
- Agents read specs before acting
- All outputs committed or versioned

## Folder Rules
/spec = system law
/prompts = agent definitions
/src = future implementation code
/docs = human-readable explanations

## Change Management
- Spec changes require commit
- No silent architectural drift
- Version history must be preserved

## Error Handling
- Agent failures trigger retry
- Quality failures trigger rewrite
- System failures trigger rollback

## Free-Tier Governance Rules
- Always check local/Supabase cache before any external API call
- Maintain per-provider quotas (RPM/RPD) with automatic throttling
- Use exponential backoff with jitter for 429/5xx responses
- Route requests in this priority order: cache → free tier API → local model
- Log: cache_hit_rate, provider_usage, 429_rate, fallback_rate per day

## Scene Structuring Spec
Scene structuring converts research output into ordered, self-contained scenes that can be handed off to Script and Visual agents without interpretation.

**Scene schema (JSON):**
- **Required fields**
  - `scene_id` (string): Stable identifier for the scene.
  - `objective` (string): The intent/outcome of the scene.
  - `key_claims` (array): Bullet claims that must be stated in the scene.
  - `source_refs` (array): Source mapping for each key claim (list of objects with `claim` + `sources`).
  - `evidence_sources` (array): Source URLs or citation identifiers for the key claims.
  - `visual_prompt` (string): Visual guidance for the scene.
  - `narration_prompt` (string): Narration guidance for the scene.
  - `transition_note` (string): How this scene connects to the next.
- **Optional fields**
  - `start_time` (string or number): Start timestamp (e.g., `"00:00:12"` or `12.0` seconds).
  - `end_time` (string or number): End timestamp (e.g., `"00:00:32"` or `32.0` seconds).
  - `narrative_role` (string): Narrative purpose (hook, proof, insight, payoff).
  - `risk_flags` (array): Potential factual or compliance risks to verify.

**Scene rules**
- Scene count must scale with runtime and semantic density (section/beat based), not fixed caps.
- For long-form scripts over 5 minutes, target at least 10 scenes, with additional cuts for dense sections.
- Every scene must map to one of: hook, proof, insight, payoff.
- Claims must have at least one evidence source and a source_refs entry.
- Every evidence_sources entry must appear in source_refs.sources.
- Transitions must be explicit and explainable in one sentence.

**Minimal example**
```json
{
  "scene_id": "s1-hook",
  "objective": "Establish the core question and tension.",
  "key_claims": ["Inflation expectations are diverging from official CPI trends."],
  "source_refs": [
    {
      "claim": "Inflation expectations are diverging from official CPI trends.",
      "sources": ["https://example.com/source-1"]
    }
  ],
  "evidence_sources": ["https://example.com/source-1"],
  "visual_prompt": "Split-screen chart of CPI vs. consumer inflation expectations.",
  "narration_prompt": "Open with a question that contrasts official data with lived experience.",
  "transition_note": "Shift to evidence that explains the divergence.",
  "narrative_role": "hook"
}
```

## Research → Scene Consistency Rules
Scene outputs must be traceable to the research output format in PRODUCT_SPEC.

**Rules**
- Each `scene.key_claims` item must map to either `research.key_facts[]` or `research.data_points[]`.
- Each `scene.source_refs` entry must reference IDs/URLs present in `research.sources[]` or `research.data_points[].source_id`.
- If a claim cannot be mapped, the Scene Builder must flag it in `risk_flags` and request research revisions.

## Research Source Governance Fields
Research sources must include governance metadata for trust and freshness.

**Required fields (sources)**
- `source_tier`: `tier_1` | `tier_2` | `tier_3`
- `freshness_window_days`: integer maximum age allowed for the source

**Validation rules**
- Claims using Tier 3 sources require at least one Tier 1 or Tier 2 corroboration.
- If `as_of_date` exceeds the `freshness_window_days`, mark the scene with `stale_data`.

## Scene Risk Flags Vocabulary
Use only the following values in `risk_flags`:
- `missing_source` (claim lacks a valid source mapping)
- `stale_data` (source is outdated relative to the topic window)
- `causal_claim` (causation asserted; needs stronger proof)
- `regulatory_risk` (compliance or legal sensitivity)
- `sensitive_topic` (elevated audience or brand risk)

## Benchmarking Data Pipeline
Define a consistent pipeline for competitor intelligence and topic gap analysis.

**Target entities**
- Channels (publisher-level metadata)
- Videos (episode-level metadata)

**Required fields (videos)**
- `video_id`, `channel_id`, `title`, `publish_date`, `duration_sec`
- `hook_text` (first 3–5 seconds or summarized)
- `thumbnail_text` (OCR or manual extraction)
- `description_summary` (1–2 sentence abstraction)
- `topic_cluster` (normalized taxonomy tag)
- `view_velocity` (views in first 24/72 hours)
- `engagement_signals` (likes, comments, ratio)
- `retention_proxy` (if available: AVD/relative retention estimates)
- `format_tags` (analysis, explainer, debate, etc.)

**Required fields (channels)**
- `channel_id`, `channel_name`, `niche_tags`, `publish_cadence`, `avg_views_90d`

**Outputs**
- Top-performing hook patterns by topic cluster.
- Thumbnail text patterns and visual motifs correlated with CTR proxies.
- Topic gaps and underserved audience segments.
## Structured Output Schema
Use this schema for scene-level structured outputs. It can be stored as JSON and is compatible with the existing research storage by serializing the object into `research_cache.content` (string) while leaving older text-only entries untouched.

**Schema (JSON):**
- **Required fields**
  - `scene_id` (string): Stable identifier for the scene.
  - `start_time` (string or number): Start timestamp (e.g., `"00:00:12"` or `12.0` seconds).
  - `end_time` (string or number): End timestamp (e.g., `"00:00:32"` or `32.0` seconds).
  - `goal` (string): The intent/outcome of the scene.
- **Optional fields**
  - `narrative_role` (string): Narrative purpose (e.g., hook, proof, insight, payoff).
  - `visual_hint` (string): Visual guidance for the scene.
  - `audio_hint` (string): Audio/SFX/music guidance for the scene.
  - `evidence_refs` (array): Citations or source identifiers; list of strings or objects (e.g., `[{ "source": "...", "note": "..." }]`).

**Storage + compatibility rules**
- When stored in `research_cache`, serialize the JSON object into the `content` field as a string (do not change the table schema). This keeps compatibility with existing text-only research entries.
- If embedding alongside other research data, wrap the structured output with a top-level envelope to avoid collisions (example: `{ "type": "structured_output", "version": "1.0", "scenes": [ ... ] }`).
- Consumers must accept either raw text (legacy) or JSON-serialized structured output and branch based on whether `content` parses as JSON.

## Metadata Conversion Experiment Logging
To improve comment-to-click conversion, metadata generation must emit experiment logs into `metadata_experiments`.

- `experiment_type` should support `pinned_comment_conversion` in addition to packaging experiments.
- For each generated `pinned_comment_variants` candidate, log one experiment row with:
  - `video_id`
  - `experiment_type = pinned_comment_conversion`
  - `title_variant` (active title)
  - `thumbnail_variant` (variant label such as `comment_v1`)
  - `start_date`
  - `notes` (short variant summary)
- Logging failures must be non-fatal and should not block content pipeline completion.

# 🛠 Technical Specification (Cost-Efficient Edition)

## 1. LLM Strategy: Multi-Tier Free API Routing
To maintain $0 operating costs, the system routes tasks based on model strengths and free quotas.
* **Primary Engine:** **Google Gemini 1.5 Flash** (Free Tier: 15 RPM / 1,500 RPD). Used for long-form script generation and extensive web research.
* **Reasoning Engine:** **DeepSeek-V3** (Free credits/Beta tier). Used for logical planning and structured PRD mapping.
* **Local Fallback:** **Ollama (Llama 3.1 8B)**. Hosted locally to handle tasks when API rate limits are hit.

## 2. Media Production Stack (Zero-Cost)
* **Audio (TTS):** `edge-tts` (Python Library). Provides high-quality Microsoft Azure voices for free without API limits.
* **Visuals:** **Playground AI** (1,000 images/day free) or **Local Stable Diffusion** (Automatic1111) for unlimited generation.
* **Editing:** **MoviePy** for automated stitching and **CapCut Desktop** (Free version) for final human-in-the-loop polish.

## 3. Data & Automation
* **Database:** Supabase (PostgreSQL) - Cloud persistent storage
* **Orchestration:** **n8n (Self-hosted via Docker)**. Replaces Zapier/Make for unlimited workflow automation.
