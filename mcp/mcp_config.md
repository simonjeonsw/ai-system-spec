# MCP + GitHub Context Integration

## Purpose
MCP is used to inject persistent project context
into all agent executions.

This ensures:
- Agents never forget system goals
- Specs are always referenced
- Long-term coherence

## Required Context Files
Always loaded into MCP:
- spec/PRD.md
- spec/RULES.md
- spec/SYSTEM_ARCH.md
- spec/AGENTS.md
- spec/STYLE.md
- spec/EVAL.md

## MCP Context Policy
- Spec > System Prompt > User Prompt
- If conflict exists, Spec wins
- Agents must explicitly acknowledge spec load

## GitHub Integration Pattern
1. Specs live in GitHub
2. MCP pulls latest main branch
3. Agents read specs via MCP context
4. All outputs must conform to specs

## Version Discipline
- All spec changes require commit
- Agents assume latest main branch state
