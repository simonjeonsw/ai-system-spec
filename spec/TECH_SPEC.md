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
* **Database:** **SQLite** (Local). Stores "Research Cache" to prevent redundant API calls and save tokens.
* **Orchestration:** **n8n (Self-hosted via Docker)**. Replaces Zapier/Make for unlimited workflow automation.
