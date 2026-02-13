# Source Evidence Contract

## Status
Canonical (L2)

## Purpose
Elevate source/evidence to a first-class contract independent of metadata generation.

## Contract Authority
- Schema: `spec/schemas/source_evidence_contract.schema.json`
- Version: `1.0`

## Required Fields
- `source_id` (pattern: `src_<id>`)
- `source_type`
- `title`
- `url`
- `publisher`
- `published_at`
- `collected_at`
- `confidence_score`
- `schema_version`

## GEO Linkage Rule (Phase B/C Draft)
- `faq_snippets[].source_ids` must reference valid `source_id` values.
- `key_claims_for_ai[].evidence_source_ids` must reference valid `source_id` values.
- `canonical_source_urls[]` must map to known `url` values from the source-evidence contract.

## Activation Constraint
- This contract must be active before any GEO hard gate activation in Phase B/C.
