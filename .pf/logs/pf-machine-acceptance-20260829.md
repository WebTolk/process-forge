# PF Machine Acceptance Log

## 2026-08-29 10:52 - orchestrator

Task: Create governed machine acceptance run and non-overlapping assignments.
Files changed: New run, assignments, and assignment capsules under .pf.
Artifacts changed: Acceptance task structure.
Templates used: ProcessForge run/task/capsule contracts.
Tools used: ProcessForge CLI.
Decisions: Stable installation changes remain main-agent owned; mechanical audits use gpt-5.3-codex-spark.
Risks: Existing post-1.1.0 source tree is dirty and release-pack currently fails.
Next steps: Launch baseline and release-surface audits.
Handoff: None.

## 2026-08-29 10:58 - orchestrator

Task: Launch baseline and release-surface Spark workers.
Files changed: Worker runtime state and launch prompts.
Artifacts changed: None yet.
Templates used: codex-exec runtime driver.
Tools used: worker-run prepare/start.
Decisions: Replaced unsuitable generic-shell invocation with the product codex-exec driver.
Risks: Initial command state persisted the inherited host environment.
Next steps: Stop launch path and repair secret persistence before retry.
Handoff: Security remediation assigned to orchestrator-main.

## 2026-08-29 11:03 - orchestrator

Task: Prevent inherited environment secret persistence.
Files changed: tools/processforge.py; tools/smoke_worker_environment_secret_redaction.py.
Artifacts changed: worker-env-secret-redaction.md.
Templates used: Focused smoke regression.
Tools used: py_compile, focused smoke, git diff --check, worker-run.
Decisions: Persist only PF-owned and explicit env values; materialize host inheritance in memory at process launch.
Risks: Explicit literal driver variables remain durable by contract and must not contain credentials.
Next steps: Continue baseline audits and source qualification.
Handoff: Two Spark workers running after remediation.
## 2026-08-29 11:32 - developer

Task: Unify local-search runtime resource resolution after the full release gate reproduced a fresh-to-stale index regression.
Files changed: tools/processforge.py; tools/pf_runtime/session_read.py; tools/smoke_project_init_local_search_mcp.py
Artifacts changed: .pf/artifacts/pf-machine-acceptance-20260829/search-resolver-consistency.md
Templates used: assignment capsule pf-search-resolver-consistency-20260829
Tools used: ProcessForge task/capsule lifecycle, py_compile, focused MCP and Garage smoke tests
Decisions: Use processforge_core.garage.snapshot_with_resolved_search_roots as the single runtime snapshot resolver for maintenance, Garage search, and session context.
Risks: Full public release-test and extracted archive validation still require a clean rerun.
Next steps: Refresh candidate checksums, amend its local provenance commit, and rerun the public release gate.
Handoff: Remains with orchestrator-main.

## 2026-08-29 12:09 - release engineer

Task: Build and qualify the isolated local ProcessForge 1.2.1 candidate.
Files changed: Candidate-only version, update index, changelog, migration note, checksum inventory, and local provenance commit.
Artifacts changed: .pf/artifacts/pf-machine-acceptance-20260829/hardening-report.md; acceptance-matrix.md
Templates used: ProcessForge release manifest and core update contracts.
Tools used: release-check, release-test, release-pack, release-archive-test.
Decisions: Keep the candidate unpublished and outside the source checkout; retain the original 1.1.0 archive for rollback evidence.
Risks: Installed upgrade, fresh hosted MCP, live hooks, Joomla behavior, and exact rollback parity remain unverified.
Next steps: Run isolated update/rollback matrix, then update the stable installation.
Handoff: pf-isolated-update-matrix-20260829.

## 2026-08-29 12:27 - reviewer

Task: Independently verify the target-side 1.2.1 updater against an isolated 1.1.0 installation copy.
Files changed: None outside governed evidence.
Artifacts changed: .pf/artifacts/pf-machine-acceptance-20260829/target-updater-review.md
Templates used: Assignment capsule pf-target-updater-review-20260829.
Tools used: 1.2.1 core-update plan, apply, status, repair; checksum verification.
Decisions: Treat the 1.1.0 updater only as transition evidence; make the 1.2.1 updater the release criterion.
Risks: Real installed Runtime/MCP lifecycle and final machine rollback are not covered by this isolated review.
Next steps: Complete isolated matrix governance and update D:\.agents\processforge with the qualified 1.2.1 archive.
Handoff: pf-installed-upgrade-acceptance-20260829.

## 2026-08-29 12:44 - developer

Task: Repair false Runtime degraded status reproduced on the real Agent Ledger after installing 1.2.1.
Files changed: tools/pf_runtime/service.py; tools/smoke_runtime_status_timeout.py.
Artifacts changed: .pf/artifacts/pf-machine-acceptance-20260829/runtime-status-timeout-remediation.md
Templates used: Assignment capsule pf-runtime-status-timeout-remediation-20260829.
Tools used: component timing, focused Runtime smokes, candidate checksum refresh, release-pack, archive structural test, real core-update apply.
Decisions: Keep reconciliation in scheduler; make status read cached host state and read the NDJSON journal tail in bounded blocks.
Risks: Full extracted-archive suite for the final candidate hash remains a final release gate.
Next steps: Run a fresh installed-MCP Joomla project workflow and collect hooks, chat, telemetry, and runtime evidence.
Handoff: pf-installed-upgrade-acceptance-20260829 continues.
## 2026-08-29 14:56 - orchestrator-main

Task: Final installed PF, Joomla, MCP, hooks and telemetry acceptance.
Files changed: governed source fixes and acceptance reports; Joomla test project artifacts.
Artifacts changed: MCP remediation, installed upgrade, Joomla acceptance and telemetry review.
Templates used: assignment capsules and PF report contracts.
Tools used: target-side core updater, extracted archive release-test, PF Runtime/MCP, Codex worker driver, Joomla CLI, PHPUnit, PHPCS, Phing and HTTPS frontend check.
Decisions: trust only complete PF-only Codex hook configurations; retain bounded `derived_reports` in MCP context.
Risks: Spark quota unavailable; browser backend unavailable; Joomla knowledge search returned no narrow article.
Next steps: rollback installed PF to original 1.1.0 and verify exact baseline parity plus Runtime/MCP restart.
Handoff: orchestrator-main retains final restoration.

## 2026-08-29 15:05 - orchestrator-main

Task: Restore the machine to ProcessForge 1.1.0 and close full acceptance evidence.
Files changed: No installed files outside the target-side updater transaction; governed review, matrix and handoff artifacts updated.
Artifacts changed: .pf/reviews/pf-machine-acceptance-20260829-final-review.md; .pf/artifacts/pf-machine-acceptance-20260829/acceptance-matrix.md; .pf/handoffs/runs/pf-machine-acceptance-20260829-handoff.md.
Templates used: ProcessForge final review, logging and handoff contracts.
Tools used: installed core-update plan/apply, SHA-256 owned-file verification, Runtime ready/doctor/tick, Windows process inspection.
Decisions: Restore the original 1.1.0 without local patching; classify its ready-but-degraded scheduler timeout as a known old-version condition.
Risks: Candidate remains local and uncommitted; promotion requires review. Spark and browser acceptance substitutions remain recorded.
Next steps: Close final review and orchestration tasks; preserve the failed baseline worker state as launcher evidence if PF does not allow recovery.
Handoff: maintainer reviews the candidate diff and decides release promotion.
