# T02 log

## 2026-09-25 23:49 +04:00 - primary
Task: preflight and governed scope.
Files analyzed: assignment/capsule, r01/r02 plan, T01 contract and T09 handoff.
Artifacts changed: scope.md, evidence/00-context.json and 00-start.json.
Templates used: pinned orchestration/intake obligations.
Tools used: actual MCP context/start, Serena config/symbol attempt, scoped UTF-8 shell fallback.
Decisions: separate T02 Work; no context refresh or legacy run continuation. Local source lifecycle; junior authorization persists.
Risks: Serena has no active language; source mapping uses scoped fallback. Current index readiness alone does not prove project grant coverage.
Next steps: accept scope, investigate service/capsule/material paths and reproduce A/B behavior.
Handoff: T01 design, T09 completed optional diagnostics.

## 2026-09-26 00:06 +04:00 - primary
Task: accepted domain/architecture and implemented shared Work read service/CLI/MCP integration.
Files changed: work_resources.py, process_execution.py, garage.py, local_resource_search.py, CLI/MCP routes and additive schemas.
Artifacts changed: before reproduction, investigation/domain/architecture, evidence 03-05 and developer probe.
Templates used: pinned process evidence obligations.
Tools used: scoped source reads, actual MCP stage transitions, junior descriptive map.
Decisions: no shared-cache content for Work reads; exact selectors/current auth before material; portable byte-hash manifest and fixed budgets. New work_resource_material.py is an explicit architecture scope refinement.
Risks: implementation not yet accepted; material module and docs are in progress, followed by source regressions and independent review.
Next steps: integrate material helper, run developer probe, complete docs, then assurance matrix.
Handoff: junior t01_capsule_map solely owns work_resource_material.py and private implementation report; junior t02_docs solely owns new EN/RU work-resources.md and private docs report. Primary retains service/integration/schema/transition ownership.

## 2026-09-26 00:24 +04:00 - primary
Task: developer probe accepted, assurance started and compatibility matrix passed.
Files changed: generated-document budget strengthening; internal-ref schema embedding compatible with existing validator; public source-status/doc links.
Artifacts changed: implementation.md, evidence/06.json, positive source CLI/MCP probe, assurance-results.json (9 PASS), test plan/cases.
Templates used: pinned implementation/assurance obligations.
Tools used: source fixture and nine focused smokes; independent junior source review and disjoint new regression author.
Decisions: keep legacy metadata fixture result and existing registrar unsupported external-ref observation. Explicit indexing is declared only in temporary test package. No broader registrar repair.
Risks: final new negative regression/review/validators pending. Source-only feature; installed qualification T06.
Next steps: inspect new test and independent findings; final schema/public/checksum checks before acceptance.
Handoff: material/docs ownership returned to primary. Junior t01_capsule_map now owns only smoke_work_resource_binding.py/report; junior t02_review writes only worker-code-review.md and no product files.

## 2026-09-26 00:46 +04:00 - primary
Task: T02 accepted and completed.
Files changed: explicit SQLite closure in new coverage and Work in-memory search; final regression/report and checksum inventory.
Artifacts changed: review-findings, test-report, delivery/evolution, final-checks, connection-verification, evidence 07-09, dedicated handoff.
Templates used: assurance/delivery/evolve obligations.
Tools used: focused smokes, schema/public/checksum, actual MCP transitions, source run-doctor (21 PASS), junior independent follow-up review.
Decisions: repair real SQLite leak exposed by Windows cleanup, remove gc test workaround. New test and nine compatibility smokes pass; source accepted. All writer ownership returned to primary.
Risks: symlink OS branch unavailable; actual-host feature integration remains T06. No release or installed-update claim.
Next steps: separate T03 Work automatically.
Handoff: .pf/handoffs/t02-work-resources-20260925.md.
