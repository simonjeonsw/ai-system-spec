# /spec/AGENT_ARCHITECTURE.md
# Agent Architecture & Boundary Contract

## Status
Canonical (L1)

## 1. Canonical Pipeline Reference
Use `spec/SYSTEM_ARCH.md` → Canonical Pipeline Contract v1.

## 2. Stage Responsibility Contracts

### 2.1 Research Agent
- Collect and structure evidence-backed facts.
- No narrative ownership.

### 2.2 Plan Agent
- Select strategy/topic and prioritize business outcome.
- No script or rendering ownership.

### 2.3 Script Agent (Semantic Source of Truth)
- Owns narrative meaning and claim phrasing.
- Downstream stages may not alter semantic intent.

### 2.4 Scene Agent (Structure & Timing Only)
- Owns sequence, pacing, transitions, and script references.
- Must not own static visual composition or animation directives.

### 2.5 Image Agent (Static Visual Assets Only)
- Owns static visual asset contract from scene intent.
- Must not change scene structure or script semantics.

### 2.6 Motion Agent (Temporal Animation Only)
- Owns animation timing/easing/transition directives.
- Must not invent new visual meaning beyond image contract.

### 2.7 Metadata Agent
- Owns title/description/tags/packaging metadata.
- Must not mutate upstream content contracts.

### 2.8 Validate Agent
- Enforces schema/boundary/quality contract checks.
- Blocks release on contract violation.

## 3. Forbidden Actions Matrix
| Stage | Forbidden |
| --- | --- |
| scene | image prompt styling, camera/lens directives, animation/easing directives |
| image | modifying script text, changing scene timing/order, adding motion directives |
| motion | changing scene sequence, modifying static composition contract, adding new claims |

## 4. Boundary Violation Handling
- Any violation is a contract error.
- Violations must be logged and blocked at validate stage.

## 5. Change Governance
- Boundary contract changes require ADR and schema updates.
