# Execution Plan (Goal: $2K/month per channel)

## Operating Constraint
All specs, tasks, and artifacts must be written in English.

## Phase 0 — Validation (Pre-Revenue)
**Goal:** Prove end-to-end automation using free-tier services only.
- Deliverables
  - Topic selection pipeline (weekly batch)
  - Research → Script → QA → Publish flow with minimal human review
  - Basic performance logging (CTR, AVD, RPM)
  - Optional multi-skill execution for fast internal drafts (see MULTI_SKILL_MODE.md)
- Exit Criteria
  - 10+ published videos
  - Stable upload cadence (>= 2/week)
  - KPI baseline documented

## Phase 1 — Reliability & Cost Control
**Goal:** Stabilize pipeline and minimize failures.
- Deliverables
  - Cache-first governance fully enforced
  - Retry/backoff and fallback routing
  - Quality gate with rewrite triggers
- Exit Criteria
  - Cache hit rate > 50%
  - 429 rate < 2%
  - Rewrite rate tracked and trending down

## Phase 2 — Scaling (Multi-Channel Readiness)
**Goal:** Repeatable output across multiple channels.
- Deliverables
  - Channel templates (tone, format, visuals)
  - Topic clustering and scheduling
  - Shared research cache and attribution tracking
- Exit Criteria
  - Two channels operating with separate configs
  - Consistent KPI reporting per channel

## Phase 3 — Revenue Optimization
**Goal:** Sustain $2K/month with measurable improvement loops.
- Deliverables
  - KPI-driven topic scoring
  - A/B testing for hooks and thumbnails
  - Monthly performance review and spec updates
- Exit Criteria
  - Revenue target met for 2+ consecutive months
  - Documented optimization playbook

## Foundation Checklist (Must Be True)
- Specs are current and versioned in Git
- Cache and quota policy enforced in code
- Quality evaluation triggers are defined and used
- Run logs and metrics are stored and reviewable
- ADRs document material architecture decisions
- KPI thresholds and rewrite triggers defined (see EVAL.md)

## Observability Policy (SLIs/SLOs)
**SLIs**
- Stage latency (p50/p95)
- Failure rate per stage
- Retry rate per stage
- Cache hit rate
- Cost per run

**SLOs (targets)**
- p95 stage latency: <= 10 minutes
- Failure rate: < 2% per stage/week
- Retry rate: < 5% per stage/week
- Cache hit rate: > 50% (Phase 1+)

**Alerting**
- Page on two consecutive SLO breaches or any publish-stage failure.
- Log incidents and link to OPERATIONS.md runbook.

## Missing Essentials (Create if not present)
- Run log schema and storage target (see SCHEMA.md: pipeline_runs)
- ADR template and decision workflow
- Operator handoff checklist
- KPI definitions with thresholds and triggers
- Observability policy and runbook (OPERATIONS.md)
- Validation plan and quality gate (VALIDATION_PLAN.md)
- Executive reporting format (REPORTING.md)
- Security and access control requirements (SECURITY.md)

## Continuity Protocol (CTO/Agent Change)
- New owner must complete Handoff checklist
- All major changes require an ADR entry
- All specs must be updated before code changes
- Weekly review: KPI trend, failures, and cost usage
- Weekly executive summary required (see REPORTING.md)

## Release Governance
- Use semantic versioning for specs and prompts (MAJOR.MINOR.PATCH).
- Record release notes and rollback steps in ADR entries.
- Run validation checks before release (see VALIDATION_PLAN.md).
- Require release notes for any minor/major release (see RELEASE_NOTES.md).

## Release Checklist
- Specs updated and committed
- Validation suite passed (schema + integration sample run)
- ADR logged for material changes
- Rollback plan documented

## Current Work Order (Priority)
1. Maintain the Planner → Topic Scoring → Research → Scene Builder → Script → QA → Ops execution chain.
2. Keep research outputs compliant with the Product Spec format.
3. Enforce Scene Structuring Spec before script drafting.
4. Apply Scene-Level QA checklist prior to any publishing workflow.
5. Enforce KPI thresholds and rewrite triggers before publish (see EVAL.md).
6. Apply channel governance rules before Ops publish (see EVAL.md).

## Handoff Checks
- Research inputs must reference the selected Planner topic and include topic_candidates scoring context.

## Phase 2 Scaling Checklist
- Channel configuration stored and validated for each channel.
- Per-channel cost tracking and KPI reporting enabled.
- Access controls for publish approvals verified.
