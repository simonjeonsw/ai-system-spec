# Section Relocation Map (Spec Refactor)

## Purpose
Track deterministic section moves from legacy locations to canonical contract files.

## Relocation Entries
| Source File | Source Section | Target File | Target Section |
| --- | --- | --- | --- |
| README.md | Execution Model | spec/SYSTEM_ARCH.md | Canonical Pipeline Contract v1 |
| howtorun.txt | Stage order lines | spec/SYSTEM_ARCH.md | Canonical Pipeline Contract v1 |
| spec/EXECUTION_PLAN.md | Flow references | spec/SYSTEM_ARCH.md | Canonical Pipeline Contract v1 |
| spec/AGENT_APPLY_GUIDE.md | Canonical Workflow | spec/SYSTEM_ARCH.md | Canonical Pipeline Contract v1 |
| spec/STRUCTURE_DESIGN_SPEC.md | Scene role rules | spec/AGENT_ARCHITECTURE.md | Stage Responsibility Contracts |
| spec/TECH_SPEC.md | Scene/image/motion mixed rules | spec/SCHEMAS.md | Forbidden Field Contract |
| spec/AGENTS.md | Agent responsibility list | spec/AGENT_ARCHITECTURE.md | Stage Responsibility Contracts |

## Verification Rule
Every relocation entry must be reflected in ADR/release notes when executed.
