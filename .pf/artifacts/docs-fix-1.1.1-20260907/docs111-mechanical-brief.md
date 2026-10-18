# D01 D05 D08: bounded documentation examples

You are a bounded PF shell worker explicitly requested by the operator. The orchestrator owns Run/Task lifecycle and .pf state: do NOT call pf.work.start/transition, session-start, task-complete, update manifest/capsules, start infrastructure, or delegate. Read your assignment capsule and this brief; no full-project bootstrap is needed. Use apply_patch for edits; read UTF-8 explicitly on PowerShell. Preserve all existing unrelated changes, especially tools/processforge.py and the required-output fix. Write only assigned files; do not change VERSION, CHANGELOG, checksums or publish/install/update anything. No network research is needed: current local source is authority. Repository temp dirs only .pf/tmp/. Return a complete Markdown report as your final response, with timestamp, files changed, exact checks/results and residual risks; the launcher captures it as expected report. Do not claim completion on mere file existence.

## Assignment

Fix audit D01, D05, D08 only. Read .pf/artifacts/docs-audit-1.1.1-report-20260907.md. For D01 synchronize RU search-index CLI (remove unsupported --project-root from five commands) and maintenance semantics with docs/concepts/resource-search-index.md; preserve project query authorization. D05 required_outputs must be a mapping with id example-report, path .pf/artifacts/example-report.md, type markdown, required true. D08 default checksums validator checks existing public inventory; --write explicitly writes; it does not validate capsules. Explain actual context/capsule doctors only after checking CLI help. Do not rewrite unrelated text. Read relevant code definitions named in audit. Run git diff --check limited to your files and parse all five revised search examples via core.build_parser without dispatch.

## Allowed product writes

## Review feedback for attempt 2 (mandatory)

The orchestrator rejected attempt 1 as incomplete. Keep the good command/output-mapping fixes. Finish D01 prose: compare English resource-search-index.md lines 68-98 and synchronize RU index_state, refresh and Runtime maintenance paragraphs. They still incorrectly say current project snapshot and periodic tick for known projects. Describe Workplace catalog readiness/refresh independent of project snapshot; preserve authorization of individual search queries by project snapshot. D08 should start "Checks the current public files against the existing deterministic SHA-256 inventory." Do not say the default command creates an inventory. Explain --write as an explicit mutation, default/--check as comparison. Add separate correct context/capsule doctor commands after checking help, e.g. project-context-check and capsule-doctor only if actually supported with correct required flags. Main source reads are allowed by allowed_read_files; forbidden_files prohibit writes to those sources, not the explicitly granted read access. Run parser checks with sys.path.insert(0, 'tools') before import processforge. Final report must explicitly address this review feedback.

- docs/ru/concepts/resource-search-index.md
- docs/concepts/assignment-front-matter.md
- docs/validation/validation.md
