# Documentation Codebase Audit - 2026-08-05

## Scope

Checked documentation against the current ProcessForge implementation for:

- runtime drivers and shell-agent launch behavior;
- `codex-exec` model, reasoning effort, and workspace access propagation;
- update server terminology and update lifecycle documentation;
- installed ProcessForge distribution updates versus project `.pf` updates.

## Code-Verified Facts

- Built-in runtime drivers are `manual`, `generic-shell`, `codex-exec`,
  `test-echo-worker`, and `test-shell-agent`.
- `worker-run prepare/start` accept `--reasoning-effort` with values
  `minimal`, `low`, `medium`, and `high`.
- `task-create` can store `agent_reasoning_effort` and workspace access grants
  through `--workspace-knowledge-resource`, `--workspace-template`,
  `--workspace-tool`, and `--workspace-mcp`.
- `orchestrator-shell-plan-apply` accepts `--model`, while reasoning effort is
  resolved from plan fields (`runtime.reasoning_effort`, worker
  `reasoning_effort` / `agent_reasoning_effort`) or worker-run overrides.
- `codex-exec` receives the model through `PF_AGENT_MODEL` or the explicit
  operator override `PF_CODEX_MODEL`; it now fails if neither is set.
- `codex-exec` maps `PF_CODEX_REASONING_EFFORT` to
  `model_reasoning_effort="<value>"` only when the value is non-empty.
- Workspace grants are resolved into private
  `.pf/runtime/agent-runs/.../workspace-access.json`; public assignments and
  capsules must use resource ids or `path_ref`, not private paths.
- `project-upgrade-check` writes an assessment report and does not update
  project `.pf` files automatically.

## Findings And Fixes

- Runtime driver docs did not fully describe `codex-exec`,
  `workspace_access_path`, `agent_reasoning_effort`, or the Codex reasoning
  mapping. Fixed in English and Russian concept docs.
- Russian runtime-driver documentation had corrupted text and did not include
  `codex-exec`. Rewritten in UTF-8.
- `codex_exec_worker.py` still had a fallback model inside the runtime wrapper.
  Removed; model selection now stays with the orchestrator/operator.
- The Codex smoke test did not prove the missing-model boundary. Added a
  negative check.
- Russian update docs used the human-facing term "площадки обновлений" and had
  several unnecessary English terms. Rewritten around "сервера обновлений" and
  clearer Russian descriptions.
- Update-system docs did not explain the operational difference between
  updating the installed ProcessForge distribution and updating project `.pf`
  state. Added both procedures.

## Validation

- `python -m py_compile tools/codex_exec_worker.py tools/validate-public-cleanliness.py tools/smoke_codex_exec_worker.py` - passed.
- `python tools/smoke_codex_exec_worker.py` - passed.
- `python tools/validate-public-cleanliness.py --root .` - passed.
- `python tools/validate-process-forge-checksums.py --root . --check` - passed after checksum refresh.
- `git diff --check` - passed.
- `python bin/pf.py release-check --root .` - passed.
- `python tools/validate-process-forge-schemas.py --root .` - passed.
