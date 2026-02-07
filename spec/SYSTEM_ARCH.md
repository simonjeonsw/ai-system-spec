# System Architecture

## 1. High-Level Architecture
User / Operator
 → Control Plane
 → Agent Orchestrator
 → Specialized Agents
 → Content Pipeline (including Scene Structuring)
 → Evaluation Layer
 → Publishing & Analytics

## 2. Control Plane
- Spec Loader
- Global Project Memory
- State Management
- GitHub Integration
- MCP Context Injection
- Orchestration requirements: stage gating, dependency resolution, and handoff criteria between agents

## 3. Observability
- Agent output logs
- Performance metrics
- Error tracking
- Retry and escalation counters

## 4. Data Flow
Research
 → Script
 → Scene Structuring
 → Visual Design
 → Voice
 → Video Assembly
 → QA
 → Upload
 → Performance Feedback

## 5. Failure Handling
- Agent failure → retry
- Quality failure → rewrite
- Pipeline failure → rollback

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
