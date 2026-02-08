# Current State Assessment

## Scope
This document summarizes the repository's current implementation status versus the declared specs and roadmap.

## Snapshot (What Exists)
- **Spec-first architecture**: Comprehensive specs under `/spec` define product, architecture, validation, and operations policies.
- **Core pipeline code**: Implementation exists in `/lib` for Research, Planner, Scene Builder, Script, Metadata, QA gate, and Ops utilities.
- **Data layer alignment**: Supabase schema is defined in `spec/SCHEMA.md` and partially implemented via `lib/supabase_client.py` and stage modules.
- **Validation tooling**: `lib/validation_runner.py` exists with JSON schema checks and sample validation commands in `howtorun.txt`.

## Gaps (What Is Missing vs Spec)
- **Research governance enforcement**: Tiered sources and freshness rules are not fully enforced in code.
- **Scene-to-research traceability**: Automated mapping of scene claims to research sources is not strictly validated in the current Scene Builder flow.
- **Benchmarking pipeline**: Competitor intelligence pipeline described in `spec/TECH_SPEC.md` is not implemented.
- **Multi-channel readiness**: `channel_configs` schema exists, but channel-specific configuration is not propagated through pipeline stages.
- **Observability completeness**: Run logs exist, but SLO-based alerting and incident workflows are not automated.
- **CI validation**: Schema validation and regression checks are manual, not enforced in CI.
- **Operational orchestration**: Scheduling, approvals, and retry policies are not centralized.

## Phase Mapping (Roadmap)
- **Phase 0**: Partially complete (end-to-end CLI path exists, but governance + QA gates are manual).
- **Phase 1**: In progress (cache + retry strategies exist, but enforcement and reporting are incomplete).
- **Phase 2+**: Not started (multi-channel, SaaS templates, full orchestration absent).

## Recommended Starting Point
1. Enforce research source governance (tier + freshness + corroboration).
2. Add scene-to-research traceability validation and risk flags.
3. Create a benchmarking data ingestion pipeline aligned to schema.
4. Introduce channel config propagation and per-channel KPI targets.
5. Add CI-based validation and regression checks.
