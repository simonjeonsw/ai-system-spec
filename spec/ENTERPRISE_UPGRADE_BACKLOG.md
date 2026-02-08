# Enterprise Upgrade Backlog

This backlog defines concrete work packages to move from a solo-operator system to enterprise-grade operations.
All tasks are ordered by dependency and leverage the existing spec hierarchy.

## P0 — Governance and Quality Enforcement (Immediate)
1. **Research Source Governance Enforcement**
   - Implement tier + freshness validation and Tier-3 corroboration checks.
   - Block publish when governance checks fail.
   - Emit risk flags in research outputs.

2. **Scene-to-Research Traceability**
   - Validate each scene claim against `research.key_facts`/`data_points`.
   - Enforce `source_refs` and `evidence_sources` alignment.
   - Add automatic repair loop when validation fails.

3. **Schema + Regression Validation in CI**
   - Add GitHub Actions workflow to run schema validation on samples.
   - Fail build on schema drift or missing required fields.

## P1 — Multi-Channel Readiness (Scaling)
4. **Channel Config Propagation**
   - Load `channel_configs` per run and apply to Planner, QA, and Metadata.
   - Store run logs and costs per channel.

5. **KPI Governance Automation**
   - Tie QA gate decisions to channel KPI targets.
   - Log decisions and actions per episode in `pipeline_runs`.

6. **Content Template Library**
   - Define channel-specific templates (tone, format, CTA patterns, pacing).
   - Use templates in planner + scripter prompts.

## P2 — Benchmarking & Strategy Intelligence
7. **Competitor Benchmarking Pipeline**
   - Ingest video/channel metadata into a dedicated store.
   - Normalize hooks, thumbnails, and pacing benchmarks.
   - Provide structured planner inputs.

8. **Topic Gap Discovery**
   - Build a periodic job to surface underserved topics by cluster.
   - Feed into Planner scoring rubric.

## P3 — Ops Orchestration & Reliability
9. **Orchestration Layer**
   - Centralize scheduling, retries, and approvals.
   - Integrate with run logs and incident workflows.

10. **Incident + SLO Automation**
    - Define alert rules based on SLOs.
    - Trigger incident runbook flow with auto-tagging.

## P4 — Enterprise Compliance & Security
11. **Secrets Management**
    - Replace local `.env` reliance with managed secrets.

12. **Role-Based Access Control (RBAC)**
    - Gate publish and metadata changes by role.

13. **Audit Trails**
    - Record publish approvals and config changes with ADR references.

## Definition of Done
- Code and specs are aligned (no spec/code drift).
- Validation and governance checks are automated.
- Multi-channel configs are operational.
- Benchmarking data flows into planning decisions.
- Ops workflows are measurable, auditable, and repeatable.
