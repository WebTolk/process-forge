# D06: synchronize RU Workplace update instructions

You are a bounded PF shell worker explicitly requested by the operator. The orchestrator owns Run/Task lifecycle and .pf state: do NOT call pf.work.start/transition, session-start, task-complete, update manifest/capsules, start infrastructure, or delegate. Read your assignment capsule and this brief; no full-project bootstrap is needed. Use apply_patch for edits; read UTF-8 explicitly on PowerShell. Preserve all existing unrelated changes, especially tools/processforge.py and the required-output fix. Write only assigned files; do not change VERSION, CHANGELOG, checksums or publish/install/update anything. No network research is needed: current local source is authority. Repository temp dirs only .pf/tmp/. Return a complete Markdown report as your final response, with timestamp, files changed, exact checks/results and residual risks; the launcher captures it as expected report. Do not claim completion on mere file existence.

## Assignment

Implement D06 only: synchronize RU with current English counterparts docs/getting-started/update-system.md and docs/concepts/core-update-manifest.md. Add --workplace-root to managed upgrade plan/apply examples; describe add-only/preserve existing config migration, post-apply doctor-workplace result last-apply.json, operator confirmation and no workplace-init as updater. Keep 1.0.2 -> 1.1.0 historical version references truthful; do not invent automatic migration to 1.1.1 or edit migrations. Read current core_update.py workplace_migration_plan and updates/migrations/1.1.0-workplace-runtime-drivers.yaml. Use natural Russian; preserve existing formatting and scope. No real plan/apply against installed system. Run git diff --check and parser-only validation of changed CLI examples.

## Allowed product writes

- docs/ru/getting-started/update-system.md
- docs/ru/concepts/core-update-manifest.md

