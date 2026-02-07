# Operator Handoff Checklist

## 1) Access & Credentials
- GitHub repo access confirmed
- API keys stored and documented
- Supabase/N8N access confirmed
- Credential rotation schedule verified
- Access reviews completed for publish permissions

## 2) Current System State
- Latest specs read (MAIN_CONTEXT, SYSTEM_ARCH, TECH_SPEC, EXECUTION_PLAN)
- Last 10 pipeline runs reviewed
- Current cache hit rate, 429 rate, and fallback rate recorded

## 3) KPIs & Targets
- Current CTR, AVD, RPM baselines documented
- Rewrite triggers and thresholds confirmed
- Current revenue status recorded

## 4) Risk & Issues
- Open failures and root causes listed
- Upcoming quota resets and expected usage

## 5) Decision Log
- ADR entries updated for recent changes
- Next decisions scheduled with owners

## 5.1) Security & Audit
- Audit logs enabled for publish approvals and config changes
- PII handling requirements reviewed (see SECURITY.md)

## 6) Immediate Next Steps
- Next 7-day content plan assigned
- Priority fixes agreed and scheduled
- Confirm execution order: Planner → Research → Scene Builder → Script → QA → Ops
- Verify research outputs match the Product Spec format before scene structuring
