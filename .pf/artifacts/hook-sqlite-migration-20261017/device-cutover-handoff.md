# Handoff: source SQLite migration -> controlled device cutover

Objective: switch the actual device consumers to the qualified SQLite source, migrate existing journals without losing concurrent legacy appends, then measure Runtime CPU. PF 1.2.0 general acceptance remains a separate deferred task.

Current status: source commit `5e710da914e90888ca8fc8092f066e34b7388808` published/read back from both dev remotes. Source checks passed; actual installed Core/Runtime/MCP and device journals remain unchanged. Old running Python code does not acquire this fix merely because dev was pushed.

Input artifacts: stages/architecture.md, stages/assurance.md, stages/delivery.md, checks/*, source-manifest.json; docs/concepts/hook-journal-sqlite.md; tools/migrate-hook-journals.py. Initial CPU evidence remains in runtime-cpu-root-cause-20261017/report.md.

Required next procedure:

1. Obtain a separately governed operator scope for installed Core/service/actual host operations. The startup contract forbids ordinary source Work from installing, restarting or repairing Runtime/MCP/host hooks. Do not repeat the previously completed 1.2.0 Core apply merely to refresh a host.
2. Reconfirm actual Runtime/MCP process identity, installed source provenance and all legacy journal writers, including hook fallback processes. Prepare and qualify the exact update artifact using the existing Core-update flow; this source result alone is not an installed artifact seal.
3. Quiesce old writers using their existing lifecycle controls and retain backups. Stopping Runtime alone is insufficient if hooks or an already-loaded MCP can still append legacy files. Do not run an apply while those writers continue. Do not delete live locks.
4. Run the new migrator without --apply for the selected project/workplace and review invalid/conflict/source counts. There was one malformed legacy project JSON line in the earlier CPU investigation; the current actual source must be inspected again. Do not silently accept it. --skip-invalid is explicit, reportable data omission.
5. While writers remain quiescent, explicitly apply the reviewed migration. Verify original files unchanged, both databases ready, stored counts and IDs/provenance/integrity. Re-run safely if an import was interrupted; normal readers reject importing state.
6. Ensure all active consumers use the updated Core, including the actual connected MCP host, not only a new standalone process. Restore managed writers, deliver one hook and one retry, and verify project-local receipts/history, config overrides, pending cleanup and unchanged legacy files.
7. Measure idle and representative hook CPU before/after on the actual Runtime. Separately qualify installed, Runtime and connected-host evidence. Only then resume any broader PF 1.2.0 acceptance requested by the user.

Files not to touch: unrelated dirty .pf/process-forge.yaml, old unrelated assignments, the excluded other writer's smoke file, immutable capsules and original journals.

Known limits: existing chat transcript persistence still uses its own NDJSON reader; this slice removes the measured canonical-journal/projection scans and does not redesign all conversation storage. Optional history flags preserve required operational state and do not erase earlier data.
