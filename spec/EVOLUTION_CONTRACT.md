# Evolution Contract

## Purpose
Define deterministic evolution rules for schema changes, stage boundaries, and recomputation scope.

## Compatibility Policy
- Backward-incompatible contract changes require a major version bump.
- Backward-compatible additive changes require a minor version bump.
- Clarification-only changes require a patch version bump.
- Each contract-affecting change must reference an ADR.

## Deterministic Replay Rules
- For a fixed input set and fixed contract version, stage outputs must remain semantically equivalent.
- Any non-deterministic behavior must be explicitly documented with bounded variance rules.

## Regeneration Scope Matrix
| Changed Stage | Must Regenerate | Must Not Regenerate |
| --- | --- | --- |
| research | plan, script, scene, image, motion, metadata, validate | none |
| plan | script, scene, image, motion, metadata, validate | research |
| script | scene, image, motion, metadata, validate | research, plan |
| scene | image, motion, metadata, validate | research, plan, script |
| image | motion, metadata, validate | research, plan, script, scene |
| motion | metadata, validate | research, plan, script, scene, image |
| metadata | validate | research, plan, script, scene, image, motion |
| validate rules only | validate | all content stages |

## Stage Boundary Enforcement
- Scene owns structure and timing only.
- Image owns static visual asset contracts only.
- Motion owns temporal animation directives only.
- Boundary violations are contract errors.

## Deprecation Windows
- Deprecated contracts remain readable for 2 release cycles.
- Deprecated contracts cannot introduce normative rules.

## Change Approval
- Contract changes require ADR entry and release-note linkage.
