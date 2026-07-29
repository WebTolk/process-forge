# Review: Specialization And Project Overrides

## Status

passed

## Scope

Review the specialization/project-overrides MVP across schemas, templates,
runtime resolver, snapshot/capsule summaries, CLI commands, docs, and smokes.

## Review Checklist

- Specializations remain workplace/project resources, not core hardcoded roles.
- Project overrides do not mutate workspace resources.
- Snapshot records selected specializations, applied overrides, hashes, merge
  modes, fingerprints, reasons, and conflicts.
- Capsules include summaries only.
- Runtime logic avoids real product/tool/platform ids.
- New smokes and release gates pass.

## Current Result

Targeted new specialization and project override smokes pass. Public
`release-test`, `release-pack`, extracted archive full validation, checksum
validation, public cleanliness, schema validation, and `git diff --check` pass.

## Residual Risks

- `overlay`, `replace`, and `fork` are schema-supported and recorded, but the
  MVP resolver only has concrete behavior for `disable`, `extension`, and
  `parameterize`.
- Arbitrary deep merge of specialization override YAML is not implemented in
  this slice.
