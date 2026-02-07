# Operations Runbook

## Incident Response
1. Acknowledge alert and identify affected stage(s).
2. Check pipeline_runs for error_summary and recent retries.
3. Apply retry or fallback routing per TECH_SPEC.
4. If publish stage fails, pause publishing and notify Ops owner.
5. Log incident details and resolution in ADR or incident notes.

## Escalation Rules
- Two consecutive SLO breaches: escalate to CTO/lead operator.
- Any publish-stage failure: immediate escalation to Ops.

## Observability Events
Each stage must log:
- run_id, stage, status, attempts
- input_refs, output_refs
- metrics: latency, tokens, cost, cache_hit

## Run-Log Emission Policy
**Planner**
- Log after topic scoring and final selection.
**Research**
- Log after research output generation and source governance validation.
**Scene Builder**
- Log after scene generation and source_refs mapping.
**Script**
- Log after script draft and after QA rewrite cycles.
**QA**
- Log after checklist evaluation with pass/fail summary.
**Ops**
- Log after publish attempt and after metadata experiment creation.

**Required metrics per stage**
- latency_ms, tokens, cost_usd, cache_hit, retry_count

## Post-Incident Review
- Identify root cause and mitigation.
- Update specs and runbook if gaps were found.
