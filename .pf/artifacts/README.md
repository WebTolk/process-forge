# ProcessForge project artifacts

Start here for the current project knowledge and delivery evidence. Updated on
2026-09-27 by the governed artifact-completion Work.

## Current project knowledge

- [Project profile](project-profile.md): purpose, layers and supported behavior.
- [Repository map](repository-map.md): code, product data and private process state.
- [Project conventions](project-conventions.md): ownership, evidence and delivery.
- [Tools](toolchain-detection-report.md), [MCP](mcp-capability-report.md),
  [templates](template-matching-report.md), [resource selection](global-resource-matching-report.md).

## Required artifact completeness

- [Complete artifact set for this Work](artifact-completion-20260927/README.md):
  all 29 artifact definitions, with explicit applicability decisions.
- [T01-T10 coverage matrix](artifact-completion-20260927/coverage.md):
  340 mandatory artifact-ID bindings across 17 completed delivery works.
- [Machine-readable evidence](artifact-completion-20260927/coverage.json):
  exact assignment paths, hashes and historical reference findings.
- [Verification](artifact-completion-20260927/test-report.md) and
  [documentation handoff](../handoffs/artifact-completion-20260927.md).

## Accepted implementation delivery

[T07 final delivery](t07-engine-20260926/final/delivery.md) and
[closeout](t07-engine-20260926/final/closeout.md) identify installed build
`ddff5983`, the standard Core update, 1015 verified owned files and the recorded
53-check installed qualification. [T10 closeout](t10-operator-runtime-fix-20260926/closeout.md)
records completion of the local operator/monitor work. Full per-task evidence,
including T01-T09, is linked from the coverage matrix.

The qualified strict-egress route is managed HTTP/JSON on Windows. Native and
isolated-local strict routes remain unsupported. Connected host MCP reload is
not established by installed CLI tests. These boundaries are part of acceptance.

## Historical material

Older bootstrap reports, generated onboarding/classification reports, proposals,
reviews and run summaries retain their original date and meaning. Root files
such as `changed-files.md` and `consolidated-roadmap.md` describe bootstrap work;
they are not current delivery summaries. Hash-recorded evidence and capsules
must not be rewritten to make a new report appear complete.

New artifacts follow [artifact-template](../../templates/artifact-template.md).
Use current context/Work state for lifecycle truth; this index is navigation.
