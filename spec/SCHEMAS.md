# JSON Schemas (Module I/O)

Schemas define the canonical inputs and outputs for each module.

## Planner Output Schema (v1.0)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PlannerOutput",
  "type": "object",
  "required": [
    "topic_candidates",
    "topic",
    "target_audience",
    "business_goal",
    "monetization_angle",
    "retention_hypothesis",
    "content_constraints",
    "research_requirements",
    "selection_rationale",
    "schema_version"
  ],
  "properties": {
    "topic_candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["topic", "scores", "total_score"],
        "properties": {
          "topic": { "type": "string" },
          "scores": {
            "type": "object",
            "required": [
              "audience_fit",
              "novelty",
              "monetization_potential",
              "evidence_availability",
              "production_feasibility",
              "viral_potential"
            ],
            "properties": {
              "audience_fit": { "type": "number" },
              "novelty": { "type": "number" },
              "monetization_potential": { "type": "number" },
              "evidence_availability": { "type": "number" },
              "production_feasibility": { "type": "number" },
              "viral_potential": { "type": "number" }
            }
          },
          "total_score": { "type": "number" },
          "notes": { "type": "string" }
        }
      }
    },
    "topic": { "type": "string" },
    "target_audience": { "type": "string" },
    "business_goal": { "type": "string" },
    "monetization_angle": { "type": "string" },
    "retention_hypothesis": { "type": "string" },
    "content_constraints": { "type": "array", "items": { "type": "string" } },
    "research_requirements": { "type": "array", "items": { "type": "string" } },
    "benchmark_insights": { "type": "object" },
    "selection_rationale": { "type": "string" },
    "schema_version": { "type": "string" }
  }
}
```

## Research Output Schema (v1.0)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ResearchOutput",
  "type": "object",
  "required": [
    "executive_summary",
    "key_facts",
    "key_fact_sources",
    "data_points",
    "sources",
    "contrarian_angle",
    "viewer_takeaway",
    "schema_version"
  ],
  "properties": {
    "executive_summary": { "type": "string" },
    "key_facts": { "type": "array", "items": { "type": "string" } },
    "key_fact_sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim", "source_ids"],
        "properties": {
          "claim": { "type": "string" },
          "source_ids": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "data_points": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["metric", "value", "timeframe", "source_id"],
        "properties": {
          "metric": { "type": "string" },
          "value": { "type": "string" },
          "timeframe": { "type": "string" },
          "source_id": { "type": "string" }
        }
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "source_id",
          "title",
          "url",
          "as_of_date",
          "source_tier",
          "freshness_window_days"
        ],
        "properties": {
          "source_id": { "type": "string" },
          "title": { "type": "string" },
          "url": { "type": "string" },
          "as_of_date": { "type": "string" },
          "source_tier": { "type": "string" },
          "freshness_window_days": { "type": "number" }
        }
      }
    },
    "contrarian_angle": { "type": "string" },
    "viewer_takeaway": { "type": "string" },
    "schema_version": { "type": "string" }
  }
}
```

## Scene Builder Output Schema (v1.0)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SceneOutput",
  "type": "object",
  "required": [
    "scene_id",
    "objective",
    "key_claims",
    "source_refs",
    "evidence_sources",
    "visual_prompt",
    "narration_prompt",
    "transition_note",
    "schema_version"
  ],
  "properties": {
    "scene_id": { "type": "string" },
    "objective": { "type": "string" },
    "key_claims": { "type": "array", "items": { "type": "string" } },
    "source_refs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim", "sources"],
        "properties": {
          "claim": { "type": "string" },
          "sources": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "evidence_sources": { "type": "array", "items": { "type": "string" } },
    "visual_prompt": { "type": "string" },
    "narration_prompt": { "type": "string" },
    "transition_note": { "type": "string" },
    "schema_version": { "type": "string" }
  }
}
```

## Script Output Schema (v1.0)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ScriptOutput",
  "type": "object",
  "required": ["script", "citations", "schema_version"],
  "properties": {
    "script": { "type": "string" },
    "citations": { "type": "array", "items": { "type": "string" } },
    "schema_version": { "type": "string" }
  }
}
```

## Schema Versioning
- Increment MAJOR for breaking field changes.
- Increment MINOR for backward-compatible additions.
- Increment PATCH for clarifications only.
