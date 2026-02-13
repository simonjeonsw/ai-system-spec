# System Architecture

## 1. High-Level Architecture
User / Operator
 → Control Plane
 → Agent Orchestrator
 → Specialized Agents
 → Content Pipeline
 → Validation Layer
 → Publishing & Analytics

## 2. Canonical Pipeline Contract v1 (Authoritative)
**Canonical order:**
`research → plan → script → scene → image → motion → metadata → validate`

### 2.1 Stage Ownership Summary
- research: source-backed factual substrate
- plan: topic and monetization strategy selection
- script: semantic source-of-truth narrative
- scene: structure/timing segmentation only
- image: static visual asset specification only
- motion: temporal animation directives only
- metadata: packaging outputs for platform publishing
- validate: contract and quality gate

### 2.2 Stage Skip Rules (Cache-hit Only)
- Stage execution may be skipped only via cache-hit of the same contract version.
- Skip logic must not reorder stage dependencies.
- Any upstream semantic change invalidates downstream cache according to regeneration scope matrix.

### 2.3 Stage Name Normalization
| Canonical Stage | Common Runtime Alias | Primary Artifact |
| --- | --- | --- |
| research | researcher | `data/<video_id>_research.json` |
| plan | planner | `data/<video_id>_plan.json` |
| script | scripter | `data/<video_id>_script_long.json` |
| scene | scene_builder | `data/<video_id>_scenes.json` |
| image | imaginer/visual | `data/<video_id>_image.json` (target contract) |
| motion | motion | `data/<video_id>_motion.json` (target contract) |
| metadata | metadata_generator | `data/<video_id>_metadata.json` |
| validate | validation_runner/validator | `data/<video_id>_validation_report.json` |

## 3. Control Plane
- Spec loader and contract resolver
- State management and dependency gating
- MCP context injection
- Change governance via ADR

## 4. Observability
- Per-stage run logs
- SLO tracking and incident linkage
- Contract drift checkpoints pre-release

## 5. Failure Handling
- Stage failure → bounded retry
- Contract failure → block release
- Publish failure → rollback + incident log

## 6. Security and Access
- Role-gated publish actions
- Secret handling policy via `spec/SECURITY.md`

## 7. Multi-Channel Tenancy
- Channel-specific configs and KPI targets
- Shared infra with channel-level attribution

## 8. Normative References
- Agent boundaries: `spec/AGENT_ARCHITECTURE.md`
- Interface contracts: `spec/SCHEMAS.md`, `spec/schemas/*.schema.json`
- Regeneration scope: `spec/EVOLUTION_CONTRACT.md`
