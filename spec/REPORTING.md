# Executive Reporting

Executive reports summarize performance, risks, and decisions for stakeholders.

## Weekly Executive Summary Template
**Period:** YYYY-MM-DD → YYYY-MM-DD

**KPI Deltas**
- CTR: <value> (Δ week-over-week)
- AVD: <value> (Δ week-over-week)
- RPM/CPM: <value> (Δ week-over-week)
- Publish cadence: <value>

**Top Wins**
- Best-performing title/thumbnail experiments (reference metadata_experiments).
- Highest retention episode and key driver.

**Top Risks**
- Failures or SLO breaches (reference pipeline_runs).
- Emerging content or compliance risks.

**Decisions & Actions**
- Decision: <keep/iterate/rollback>
- Owner: <name>
- Due date: <date>

**Notes**
- Link to run logs and experiment logs for evidence.

## Trend Rules
- Two consecutive weeks of CTR decline → open investigation ticket.
- AVD decline > 10% week-over-week → script pacing review.
- Retention drop at 30s for 2 weeks → hook rewrite and scene audit.

## Decision Rubric
- Investigate: KPI declines exceed trend rules or SLO breach observed.
- Iterate: KPIs are flat but within thresholds; test packaging variants.
- Rollback: KPI declines persist after two iterations.
