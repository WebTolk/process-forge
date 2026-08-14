## 2026-08-14 08:20 - codex-main

Task:
Unblocked the project context and shell-worker capsule path required by the Runtime master prompt.

Files changed:
- `.pf/process-forge.local.yaml`
- `.pf/registries/tools.yaml`
- `.pf/contexts/**`
- `.pf/artifacts/project-context-refresh-report.md`
- `.pf/artifacts/runtime-context-unblock-20260814/context-unblock-report.md`
- `.pf/handoffs/runtime-context-unblock-20260814-handoff.md`

Artifacts changed:
- Context-unblock report and handoff.

Tools used:
- ProcessForge context refresh/check, assignment capsule, doctor-project, schema validation.

Decisions:
- Use the installed workplace through an ignored local manifest rather than mutate shared workplace registries.
- Declare project-local capability providers explicitly because the snapshot resolver reads project registries for capability status.

Risks:
- Refresh exit code is inconsistent with its fresh written snapshot.
- Legacy onboarding doctor failures remain outside this context slice.

Next steps:
- Complete context task and launch independent Codex shell-worker Runtime review.

Handoff:
- `.pf/handoffs/runtime-context-unblock-20260814-handoff.md`
