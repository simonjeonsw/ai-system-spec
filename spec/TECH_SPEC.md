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
