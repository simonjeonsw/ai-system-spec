# Main Context Document (MCD)

## Purpose
This document defines the absolute truth of the system.
All agents must load and follow this document before acting.

## Success Definition
Success means the system consistently ships finance/economics and adjacent channel content that improves revenue (RPM/CPM and total revenue per video), retention (AVD, retention curve stability, and return viewer rate), and automation efficiency (shortening idea → publish time while reducing rewrites and QA failures) across multiple channel types.

## System Identity
This system is an AI-native operating system for building,
testing, and scaling monetized media automation pipelines.

It is designed to:
- Prevent AI goal drift
- Preserve long-term project memory
- Enforce architectural consistency
- Enable multi-agent specialization

## Core Data Flow
Idea
 → Planning
 → Research
 → Build
 → Evaluation
 → Versioned Output (GitHub)
 → Performance Feedback
 → Iteration

## Source of Truth Hierarchy
1. MAIN_CONTEXT.md
2. Other /spec documents
3. System prompts
4. User prompts
5. Ad-hoc instructions

## Long-Term Vision
- Multi-channel automation
- Shared pipeline templates
- SaaS-style reuse
- Revenue-optimized content engines

## Non-Negotiables
- No undocumented architectural changes
- No skipping evaluation
- No intuition-only decisions
- No bypassing specs
- All project artifacts, specs, schemas, and task outputs must be written in English

## Definitions
Agent = Specialized autonomous role
Spec = System law
Pipeline = Repeatable automation flow
MCP = Context + tool protocol layer
