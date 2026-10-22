# Test plan and cases

2026-10-22. Qualify final owned bytes over clean base
a88607af49dbde56fb6672f6ad658a184dec3381, excluding unrelated WIP.

- Real normalization and unchanged matching for invalid UTF-8, valid BOM and
  invalid BOM line reporting; byte/digest preservation, no semantic blocker.
- Russian/English/other Unicode, Markdown fences of varying length, inline and
  indented code, raw paired HTML. Explicit sections/markers and bad declarations.
- Meaningful versus generic N/A reasons and bare N/A documents; missing structural
  reason/support still rejected, placeholder support explained without new rules.
- Local existing/missing/empty/angled links, unsafe root traversal, malicious
  resolver return containment, remote/anchor/code references never resolved.
- Unsupported/large/changed files have explicit coverage; actual stream read cap,
  64 reference probes, 32 findings, and separately retained limit reasons.
- Caller cannot forge a clean new review; pure state projection performs no I/O,
  clones data and leaves legacy/history untouched. Old records are not_recorded.
- Real source CLI/MCP parity after successful transition, persisted last-stage
  warnings, unchanged history after file edits, authoritative freshness diagnostic,
  valid retry and source cycle completion.
- Existing evidence-guidance suite and eight profile smoke regressions.

Registered shared launcher: pytest, lint, format, scoped mypy. No missing-import
suppression, dependency installation, broad ZIP release check or infrastructure.
Primary self-review only: capsule denies subagents. Clean snapshot/scripts and raw
results retained locally as verification evidence, sanitized summaries delivered.
