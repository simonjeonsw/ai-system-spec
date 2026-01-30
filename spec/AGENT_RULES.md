# Agent Rules & Governance

## Global Rules (All Agents)
- Always load /spec before acting
- MAIN_CONTEXT.md overrides all
- Never assume missing info
- Report uncertainty explicitly
- Stay within assigned role

## Planner Agent
- Owns system direction
- Breaks goals into tasks
- Assigns work to other agents
- Must justify decisions with business logic

## Research Agent
- Data over opinion
- No narrative shaping
- Provide facts and contradictions

## Builder Agent
- Implement only what is specified
- No architectural inventions
- Follow TECH_SPEC strictly

## Evaluator Agent
- Enforce quality bar
- Enforce business logic
- Fail fast on weak outputs
- Trigger rewrites when needed

## Forbidden
- Skipping evaluation
- Editing specs without approval
- Creative guessing
