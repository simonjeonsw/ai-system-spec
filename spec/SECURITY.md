# Security & Compliance Requirements

All security policies apply to every agent, operator, and automation workflow.

## Access Control
- Role-based access for triggering pipeline runs and publishing content.
- Publish actions require explicit approval by an authorized operator.
- Least-privilege policy for all service credentials.

## Secrets Management
- API keys must be stored in a secrets manager (no plaintext in repo).
- Secrets must never be logged in pipeline_runs or chat outputs.
- Rotate credentials on a fixed schedule or after suspected exposure.

## Audit Logging
- Log publish approvals, configuration changes, and credential rotations.
- Audit logs must include who/what/when and a reason field.

## PII & Compliance
- Avoid storing PII unless explicitly required and documented.
- If PII is unavoidable, encrypt at rest and restrict access to admins only.
- Comply with platform policies for content and data usage.

## Security Boundaries
- Only Ops or authorized roles can approve publishing.
- External integrations must be reviewed and documented in ADRs.
