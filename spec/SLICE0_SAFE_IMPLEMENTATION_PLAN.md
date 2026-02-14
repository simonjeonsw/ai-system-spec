# Slice-0 Safe Implementation Plan (Plan Mode Only)

> **Mode:** Plan Mode (No execution, no production cutover in this document).
>
> **Scope lock:** Promotion path only, single region, single execution adapter.

## 1) Baseline and Non-Negotiable Decisions

This plan uses the default safe decisions exactly as provided:

1. Workload identity: **SPIFFE**
2. Key management: **KMS**, 30-day rotation, `kid` revocation policy
3. Epoch lifecycle: **active -> drain -> deprecate**, grace window **1 minute**
4. Revocation SLA: **global p99 <= 5s**, isolate region on propagation failure
5. Fail-closed: **promotion always fail-closed**
6. Ledger timeout: approval -> commit **30s**, then **auto revoke/abort**
7. Alert channels: **Slack + PagerDuty**
8. KPI targets: **OOB=0, replay blocked=100%, promotion during hold=0, audit linkage=100%**

## 2) Independent Validation Summary

Current repository status is **NOT READY** for Slice-0 execution:

- Policy evaluation exists via `check_phase_state(payload)`.
- Execution enforcement boundary (`authorize_execution`) does not exist.
- No implemented token/JTI/epoch/revocation verification pipeline.
- No execution identity binding checks.
- No decision-to-execution drift checkpoint.
- No ledger compensation guard for approval/commit race.
- No observability bus correlation contract requiring `decision_hash + token_jti + authorization_id`.

## 3) Slice-0 Backlog (Epic / Stories / DoD / KPI / RACI)

## Epic A — Execution Boundary Hardening (Gateway)

### Story A1: Define and freeze `authorize_execution` contract
- **Description:** Create control-plane API contract as the single authorization boundary for promotion execution.
- **DoD:**
  - Request schema includes `decision_hash`, `attestation_token`, `action_scope`, `execution_identity`, `requested_at`.
  - Response schema includes `authorization_id`, `verdict`, `denial_code`, `policy_bundle_hash`, `enforcement_epoch`.
  - Explicit rule: direct promotion execution without gateway is policy violation.
- **KPI:** 100% promotion requests observed at gateway.
- **RACI:**
  - **R:** Control Plane Eng
  - **A:** CTO / System Owner
  - **C:** Security, SRE
  - **I:** Operations

### Story A2: Promotion adapter single-path enforcement
- **Description:** Wire one promotion adapter to require gateway authorization before execution.
- **DoD:**
  - Adapter fails closed on gateway timeout/error.
  - Bypass attempts emit `OOB_EXECUTION_DETECTED` event.
- **KPI:** OOB promotion attempts blocked rate = 100%.
- **RACI:** R: Platform Eng, A: CTO, C: Security/SRE, I: Operations

## Epic B — Token/JTI/Epoch/Revocation Verification

### Story B1: Minimal-safe token claim schema
- **Description:** Freeze minimal claims for Slice-0 to reduce parser drift.
- **Required claims:**
  - `decision_hash`, `jti`, `exp`, `action_scope`,
  - `policy_bundle_hash`, `enforcement_epoch`, `exec_identity_hash`,
  - `kid`, `issued_at`.
- **DoD:**
  - Schema versioned (`token_schema_version`).
  - Contract tests validate missing/extra claim behavior.
- **KPI:** schema compliance in pre-prod test traffic = 100%.
- **RACI:** R: Security Eng, A: CTO, C: Control Plane Eng, I: Operations

### Story B2: One-time JTI + revocation mesh check
- **Description:** Enforce replay prevention and revocation consistency.
- **DoD:**
  - JTI cannot be reused.
  - Revocation checks include token (`jti`), signer key (`kid`), and agent identity.
  - If revocation certainty unavailable for promotion scope, deny (fail-closed).
- **KPI:** replay blocked = 100%; revocation propagation p99 <= 5s.
- **RACI:** R: Security Eng, A: CTO, C: SRE, I: Operations

### Story B3: Epoch compatibility enforcement
- **Description:** Validate token epoch against runtime epoch state.
- **DoD:**
  - Support states: `active`, `drain`, `deprecate`.
  - Grace window exactly 1 minute (configurable but default locked).
  - Epoch mismatch yields deterministic deny code.
- **KPI:** epoch mismatch unauthorized execution = 0.
- **RACI:** R: Control Plane Eng, A: CTO, C: Security/SRE, I: Operations

## Epic C — Execution Identity Binding (SPIFFE)

### Story C1: Identity model and binding hash
- **Description:** Bind execution context to token using SPIFFE workload identity.
- **Identity fields:** `agent_id`, `pipeline_id`, `region`, `env_tier`, `spiffe_id`.
- **DoD:**
  - `exec_identity_hash` deterministic hash spec is documented.
  - Verification compares runtime identity with token-bound identity.
- **KPI:** identity mismatch unauthorized execution = 0.
- **RACI:** R: Security Eng, A: CTO, C: Platform Eng, I: Operations

### Story C2: Wrong-executor deny path
- **Description:** Add explicit deny handling and alerting for identity mismatch.
- **DoD:**
  - Denial code `IDENTITY_BINDING_MISMATCH` implemented in contract.
  - Alert routed to Slack + PagerDuty.
- **KPI:** mean detection latency < 10s.
- **RACI:** R: SRE, A: CTO, C: Security, I: Operations

## Epic D — Drift Guard and Revalidation

### Story D1: T1 checkpoint at authorization time
- **Description:** Mandatory revalidation before final allow.
- **Signals:** `phase_hold`, incident status, override validity/TTL, policy/epoch compatibility.
- **DoD:**
  - Drift check runs on every promotion authorization.
  - Drift denial code taxonomy documented.
- **KPI:** promotion during hold = 0.
- **RACI:** R: Control Plane Eng, A: CTO, C: Security, I: Operations

### Story D2: Partial re-evaluation optimization
- **Description:** Evaluate only promotion-critical signals for low-latency safety.
- **DoD:**
  - Critical-signal matrix approved.
  - p95 authorization latency target defined and measured.
- **KPI:** p95 auth latency within agreed SLO while maintaining zero unsafe allows.
- **RACI:** R: Platform Eng, A: CTO, C: SRE/Security, I: Operations

## Epic E — Ledger Compensation and Audit Integrity

### Story E1: Approval/commit split with compensation
- **Description:** Keep authorization path deterministic while guarding commit race.
- **DoD:**
  - Approval must be committed to ledger within 30s.
  - On timeout/failure, auto revoke or abort execution.
  - Reconciliation job detects `approved_without_committed_ledger`.
- **KPI:** audit linkage = 100%.
- **RACI:** R: Data Platform Eng, A: CTO, C: SRE/Security, I: Operations

### Story E2: Decision hash audit chain integrity
- **Description:** Ensure every execution event links back to `decision_hash`.
- **DoD:**
  - No execution completion accepted without linked authorization record.
  - Audit schema validation enforced in CI.
- **KPI:** orphan execution records = 0.
- **RACI:** R: Data Platform Eng, A: CTO, C: Security, I: Operations

## Epic F — Observability Bus Correlation

### Story F1: Event schema v1 for enforcement bus
- **Description:** Standardize telemetry across gateway/verifier/adapter/ledger.
- **Mandatory correlation keys:** `decision_hash`, `token_jti`, `authorization_id`.
- **DoD:**
  - Event types: request, approved, denied, execution_started, execution_completed, revocation_hit, drift_detected, compensation_triggered.
  - Schema versioning and backward compatibility rules documented.
- **KPI:** correlated event chain completeness = 100%.
- **RACI:** R: SRE/Observability Eng, A: CTO, C: Security/Platform, I: Operations

### Story F2: Alert policy for critical violations
- **Description:** Wire critical denial and anomaly signals to Slack + PagerDuty.
- **DoD:**
  - Alerts for replay, OOB, promotion-under-hold attempt, commit-timeout compensation.
  - Runbooks linked in alert payload.
- **KPI:** MTTA for critical enforcement incidents < 5 minutes.
- **RACI:** R: SRE, A: CTO, C: Security, I: Operations

## 4) Phase Sequencing (Minimum Safe Rollout)

- **Phase 1 (Contract Freeze + Skeleton):** A1, B1, C1, F1
- **Phase 2 (Enforcement Core):** A2, B2, B3, D1, E1
- **Phase 3 (Operational Hardening):** C2, D2, E2, F2

> Exit criteria: no phase advances unless phase KPI gates pass.

## 5) Identified Safety Gaps and Mitigations

1. **Gap:** No enforcement boundary in code.
   - **Mitigation:** Implement Gateway first; block direct promotion path.
2. **Gap:** No replay/epoch/revocation guards.
   - **Mitigation:** Enforce minimal-safe verification order and fail-closed policy.
3. **Gap:** No identity binding.
   - **Mitigation:** SPIFFE-based runtime binding with mismatch deny.
4. **Gap:** No drift checkpoint.
   - **Mitigation:** mandatory T1 revalidation for promotion scope.
5. **Gap:** Ledger race unresolved.
   - **Mitigation:** 30s commit timeout + automatic compensation.
6. **Gap:** Event correlation incomplete.
   - **Mitigation:** enforce correlation keys across all enforcement events.

## 6) Optional Improvements / Alternative Safer Designs

1. **Optional:** HSM-backed signing keys for high-assurance environments.
   - Better tamper resistance than KMS-only, at higher operational cost.
2. **Optional:** Reduce key rotation to 14 days once operational burden is acceptable.
   - Improves blast-radius control for key compromise.
3. **Optional:** Add Jira ticket auto-creation for post-incident traceability.
   - Complements Slack/PagerDuty by creating durable remediation workflow.
4. **Optional:** Regional revocation pre-warm cache and quorum-ack dashboard.
   - Improves confidence in p99 5s propagation compliance.

## 7) Strong Disagreement (Safety Gate)

It is unsafe to execute Slice-0 before Gateway + verification + drift + compensation are in place. The current system is a policy evaluation core, not an execution control plane.

## 8) This Was Not Asked, but Is Important Because...

A frequent production failure pattern at scale is fail-open during partial outages (IdP or network partition), not cryptographic breakage. If fail-closed semantics are not explicitly implemented for promotion scope, policy correctness will be bypassed by operational exception paths.
