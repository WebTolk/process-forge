# Documentation Audit Update Log

## 2026-08-05 07:52 - codex

Task:
Audit ProcessForge documentation against current code and update runtime-driver
and update-system documentation.

Files changed:
README.md, README.ru.md, docs/concepts/runtime-drivers.md,
docs/concepts/shell-agent-subagent-policy.md,
docs/getting-started/agent-ledger-process-transitions.md,
docs/getting-started/update-system.md,
docs/ru/authoring/update-sites-for-packages.md,
docs/ru/concepts/runtime-drivers.md,
docs/ru/concepts/shell-agent-subagent-policy.md,
docs/ru/concepts/update-lifecycle.md,
docs/ru/concepts/update-sites.md,
docs/ru/getting-started/agent-ledger-process-transitions.md,
docs/ru/getting-started/update-system.md, tools/codex_exec_worker.py,
tools/smoke_codex_exec_worker.py.

Artifacts changed:
.pf/artifacts/docs-codebase-audit-2026-08-05.md.

Templates used:
None.

Tools used:
Serena project memory, rg, ProcessForge CLI help, apply_patch.

Decisions:
Documented the code-verified runtime contract and removed the remaining
hardcoded Codex model fallback from the wrapper so the docs do not preserve a
runtime-driver model decision.

Risks:
Full release-test is not run for this documentation slice; targeted checks are
used because the change is limited to docs, the Codex wrapper model boundary,
and the related smoke.

Next steps:
No handoff is required. Commit can include the documentation updates, wrapper
boundary fix, validator exception for provider-specific runtime docs, checksum
refresh, audit artifact, and this log.

Handoff:
None.
