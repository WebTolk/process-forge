# Run Plan: Pre-release ProcessForge Product Audit

Objective: inspect the current product and release archive without modifying product code.

## Workstreams

1. Core, CLI, process catalog, configuration, and runtime contracts.
2. Entity authoring masters and create/doctor/publish parity.
3. Public release archive, clean-install behavior, and comparison with the working project `.pf`.
4. Independent reproduction and severity review of material findings.

## Constraints

- Product source and public release files are read-only.
- Only audit evidence under `.pf` may be written.
- Findings require a concrete contract reference and reproducible evidence.
- Historical `.pf` inconsistencies are reported separately from current product defects.

## Completion

- status: completed
- result: NO-GO
- report: `.pf/artifacts/pre-release-product-audit-20260730.md`
- review: `.pf/reviews/pre-release-product-audit-20260730-review.md`
- handoff: `.pf/handoffs/pre-release-product-audit-20260730-handoff.md`
