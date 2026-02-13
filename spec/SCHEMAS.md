# JSON Schemas (Module I/O)

## Status
Canonical (L2)

## Contract Authority
- Machine-readable contracts: `spec/schemas/*.schema.json`
- If prose conflicts with schema files, schema files are authoritative.

## Canonical Pipeline I/O Order
`research → plan → script → scene → image → motion → metadata → validate`

## Stage Contract Summary

### Planner Output Schema (v1.0)
- File: `spec/schemas/planner_output.schema.json`

### Research Output Schema (v1.0)
- File: `spec/schemas/research_output.schema.json`

### Script Output Schema (v1.0)
- File: `spec/schemas/script_output.schema.json`

### Scene Output Schema (v2.0 structure-only)
- File: `spec/schemas/scene_output.schema.json`
- Allowed: sequence/timing/objective/script reference/transition fields.
- Forbidden: static image composition fields, motion directives.

### Image Output Schema (v1.0 static assets)
- File: `spec/schemas/image_output.schema.json`
- Allowed: static composition/style/overlay spec by scene reference.
- Forbidden: script semantic edits, motion timeline fields.

### Motion Output Schema (v1.0 animation)
- File: `spec/schemas/motion_output.schema.json`
- Allowed: temporal directives linked to scene/image IDs.
- Forbidden: script semantic edits, scene structure changes.


### Metadata Output Schema (v1.1 SEO + GEO Phase A placeholders)
- File: `spec/schemas/metadata_output.schema.json`
- SEO fields: title, description, tags, chapters, thumbnail/pinned/community variants, runtime estimates.
- GEO Phase A placeholders (optional): `target_locale`, `target_region`, `primary_keyword`, `secondary_keywords`.
- GEO Phase B/C fields (`faq_snippets`, `key_claims_for_ai`, `canonical_source_urls`) are intentionally deferred.

## Forbidden Field Contract (Guard)
- `scene_output` must not include image/motion-owned fields such as `camera_angle`, `style_profile`, `visual_style`, `animation`, `easing`, `transition_fx`.
- `image_output` must not include motion-owned fields such as `entrance`, `exit`, `timeline`.
- `motion_output` must not include scene structure fields such as `scene_order`, `duration_reallocation`.

## Schema Versioning
- MAJOR: breaking changes
- MINOR: backward-compatible additions
- PATCH: clarifications

## Migration Rule
- Contract upgrades must include regeneration guidance in `spec/EVOLUTION_CONTRACT.md`.
