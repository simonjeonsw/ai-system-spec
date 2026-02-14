# Slice-0 Phase-1 Contract Freeze Package (Plan Mode)

> **Plan Mode only**: This document freezes contracts and test requirements. It does **not** authorize Slice-0 execution.

## Scope
- Promotion path only
- Single region
- Single execution adapter
- Fail-closed mandatory

## Frozen Contracts (Phase-1)

1. `authorize_execution` API boundary
   - Request schema: `spec/schemas/authorize_execution.request.schema.json`
   - Response schema: `spec/schemas/authorize_execution.response.schema.json`

2. Attestation token claim contract
   - Schema: `spec/schemas/attestation_token_claims.schema.json`

3. Enforcement observability event contract
   - Schema: `spec/schemas/enforcement_event.schema.json`
   - Mandatory correlation keys: `decision_hash`, `token_jti`, `authorization_id`

4. Fail-Closed Matrix contract
   - Schema: `spec/schemas/fail_closed_matrix.schema.json`
   - Mandatory rule: promotion scope must always be fail-closed

## Deterministic Verification Pipeline (Frozen)
1. Validate request schema
2. Verify token signature and token schema
3. Enforce one-time `jti` replay check
4. Verify revocation mesh status (`jti`, `kid`, `agent_id`)
5. Validate `enforcement_epoch` compatibility (`active -> drain -> deprecate`, grace=1m)
6. Enforce SPIFFE identity binding (`exec_identity_hash` vs runtime identity tuple)
7. Run T1 drift revalidation (`phase_hold`, incident, override TTL/validity)
8. Return deterministic allow/deny with denial code
9. Start ledger approval->commit timer (30s); auto revoke/abort on timeout

## Ambiguities to Resolve Before Implementation
- Canonical deny code registry owner and release cadence
- Drift signal source-of-truth priority under partial partition
- Revocation mesh quorum threshold for region isolation

## Contract Test Gate
Consumer-driven contract tests are mandatory before implementation rollout:
- API request/response schema tests
- Token claim schema tests
- Event schema tests
- Fail-closed matrix semantic tests

Slice-0 cannot proceed until these tests are green in CI.

## This was not asked, but is important because...
Without a frozen contract package and test gate, each adapter/verifier may interpret safety rules differently, causing split-brain authorization and silent fail-open behavior during incidents.
