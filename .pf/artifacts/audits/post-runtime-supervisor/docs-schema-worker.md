# Docs And Schema Worker Audit

Source: delegated read-only worker `audit-docs-schema-worker`.

Findings:

1. High: Russian documentation contains mojibake in existing top-level and `docs/ru/**` files.
2. Medium: `docs/releases/initial-release.md` still says there is no supervisor, while the new supervisor MVP is active and documented.
3. Medium: `process-supervisor` stages produce `process-record`, `worker-logs`, and `exit-record`, but those ids are not declared in `artifact_definitions`.
4. Medium: `process-supervisor` references `template: agent-run-state` and `template: worker-process-command`, but matching templates are absent.
5. Low: Russian README is stale compared with the English README for runtime driver/supervisor commands and links.

Local verification:

- Confirmed stale release note with `rg -n "No daemon, runner, supervisor|bounded file-first supervisor|supervisor"`.
- Confirmed missing artifact definitions with a targeted scan of `processes/process-supervisor.yaml`.
- Confirmed no matching `templates/*agent-run-state*` or `templates/*worker-process-command*` files are present.
