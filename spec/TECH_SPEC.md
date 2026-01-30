# Technical Specification

## Primary Tools
- GitHub (source of truth)
- Cursor (agent + MCP IDE)
- MCP servers (context + tools)

## Architecture Rules
- Markdown for all specs
- GitHub = canonical storage
- Agents read specs before acting
- All outputs committed or versioned

## Folder Rules
/spec = system law
/prompts = agent definitions
/src = future implementation code
/docs = human-readable explanations

## Change Management
- Spec changes require commit
- No silent architectural drift
- Version history must be preserved

## Error Handling
- Agent failures trigger retry
- Quality failures trigger rewrite
- System failures trigger rollback
