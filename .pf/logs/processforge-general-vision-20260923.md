## 2026-09-23 20:15 +04:00 - primary agent

Task:
Preserve the operator-provided ProcessForge general-vision quote verbatim and
add a source-verified conformance assessment.

Files changed:
- `.pf/artifacts/reference-projections/processforge-general-vision.md`

Artifacts changed:
- Added the conceptual reference projection; it is manually authored and not a
  Runtime-generated projection.

Templates used:
- None.

Tools used:
- ProcessForge context/repair interfaces, file-first context refresh, focused
  source and documentation inspection, and Git state inspection.

Decisions:
- Kept the operator quote verbatim.
- Recorded the model-neutral architecture as confirmed, while separating it
  from unsupported claims of present-day driver symmetry for every provider.
- Kept the ordinary Runtime `artifacts/projections/` directory reserved for
  generated technical projections; the durable conceptual reference is under
  `artifacts/reference-projections/`.

Risks:
- The refreshed context immediately remains stale because project-artifact
  resources and derived reports are part of the freshness surface. Existing
  legacy assignments remain untouched. No product-code or active-assignment
  change was made.

Next steps:
- Use this reference when evaluating architecture proposals. A future governed
  task may decide whether to register it as a searchable project resource.

Handoff:
- The operator quote and the corresponding assessment are self-contained in
  `.pf/artifacts/reference-projections/processforge-general-vision.md`.
