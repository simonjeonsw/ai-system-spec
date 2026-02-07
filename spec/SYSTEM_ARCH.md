# System Architecture

## 1. High-Level Architecture
User / Operator
 → Control Plane
 → Agent Orchestrator
 → Specialized Agents
 → Content Pipeline (including Scene Structuring)
 → Evaluation Layer
 → Publishing & Analytics

## 1.1 Optional Multi-Skill Execution Mode
For early-phase speed and low-risk iterations, the system can run a single agent
that performs multiple stages in one pass. This is opt-in and must still emit
per-stage run logs and schema-compliant outputs. See `spec/MULTI_SKILL_MODE.md`.

## 2. Control Plane
- Spec Loader
- Global Project Memory
- State Management
- GitHub Integration
- MCP Context Injection
- Orchestration requirements: stage gating, dependency resolution, and handoff criteria between agents

## 3. Observability
- Agent output logs
- Performance metrics (CTR, AVD, RPM)
- Error tracking
- Retry and escalation counters
- Cost governance metrics (cache hit rate, API usage, 429 rate, fallback rate)
- Run-log emission points at every stage (planner, research, scene, script, QA, ops)
- Alerting on SLO breaches (latency, failure rate, retry rate, cache-hit)
- Incident runbook reference (see OPERATIONS.md)

## 4. Data Flow
Research
 → Script
 → Scene Structuring
 → Visual Design
 → Voice
 → Video Assembly
 → QA
 → Upload
 → Performance Feedback (CTR, AVD, RPM) → Metadata/Thumbnail/Script iteration loop

Experiment Logs (metadata_experiments)
 → Packaging adjustments (titles/thumbnails)

## 4.2 Benchmarking & Competitor Intelligence Flow
Collection
 → Normalization
 → Insight Extraction (hook patterns, pacing, packaging)
 → Recommendations (topic gaps, packaging guidance)
 → Planner Inputs (topic scoring, constraints)

## 4.1 Learning Loop KPI Tracking (Research → Script → QA → Ops)
- Research: topic demand signal, competitive saturation, predicted RPM band
- Script: hook CTR proxy, projected AVD, clarity score from QA heuristics
- QA: retention risk flags, factual accuracy score, rewrite count per episode
- Ops: publish latency, CTR/AVD/RPM actuals, return viewer rate by topic

## 5. Failure Handling
- Agent failure → retry
- Quality failure → rewrite
- Pipeline failure → rollback

## 6. Cost Governance (Free-Tier First)
- Enforce cache-first lookups before any external API call
- Implement quota-aware routing (primary → secondary → local fallback)
- Apply exponential backoff and jitter on 429/5xx responses
- Log per-provider RPM/RPD usage and cache hit rate

## 7. Security & Access Boundaries
- Role-gated access to trigger pipeline runs and publish actions
- API keys stored in a secrets manager (no plaintext in repo)
- Audit logging for publish approvals and config changes (see SECURITY.md)

## 8. Continuity & Handoff
- Every pipeline run must emit a structured run log
- Each decision that changes architecture requires an ADR entry
- New operators must complete the Handoff checklist before executing changes

## 9. Multi-Channel Tenancy Model
- Each channel has a dedicated configuration profile (tone, format, KPI targets).
- Shared research cache with per-channel attribution tracking.
- Cost tracking and SLO reporting at the channel level.

# 🏗 System Architecture

## 1. High-Level Overview
The system follows a **"Cache-First, API-Last"** approach to maximize the utility of free-tier credits.

## 2. Key Components
* **The Orchestrator (Planner):** Breaks down YouTube trends into actionable sub-tasks.
* **Efficiency Layer (New):** * **Context Cache:** Checks SQLite if a similar topic was researched within the last 7 days.
    * **Rate-Limit Guard:** Monitors RPM (Requests Per Minute) to prevent 429 errors from Google/DeepSeek APIs.
* **Agent Worker Pool:** Distributed tasks across Gemini (Research), DeepSeek (Scripting), and Local TTS (Voice).
* **Human-in-the-Loop (HITL) Portal:** A simple UI (Streamlit) for the user to approve scripts before final rendering.
Centralized Data Layer: Use Supabase to sync research data and script history across sessions.
