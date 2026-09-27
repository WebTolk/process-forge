# T05 worker driver and prompt source map

Status: bounded descriptive mapping; source reads only. Serena Python symbols were unavailable, so line mapping used scoped UTF-8 reads and `rg`.

## Preparation and prompt path

- `tools/processforge.py:18958-19025`, `prepare_worker_run`: loads the assignment; validates or creates the immutable capsule; validates the execution contract with `require_ready=True`; writes private `workspace-access.json`; renders the worker prompt; resolves/validates the driver; increments attempt; builds and persists command/status; removes the prior `exit.json`; emits `worker.run.prepared`. This is the shared preparation path for manual, generic shell, and Codex drivers.
- `tools/processforge.py:19980-20065`, `render_worker_launch_prompt`: generates `.pf/runs/<run>/worker-prompts/<task>.md` with task ID, assignment/capsule refs, grants counts, allowed/read/forbidden files, required outputs, expected report and subagent rules. When knowledge-resource grants exist (`19993-20000`), it requires MCP calls in order: `pf.context`, `pf.work.start`, `pf.resolve`, `pf.search`; MCP failure blocks, with no filesystem-discovery fallback. This branch is conditional; the prompt is otherwise generic.
- `templates/worker-launch-prompt.md:1-20`: standalone prompt template carries generic scope/report instructions. The renderer builds the richer assignment-specific prompt in code; it does not simply substitute this template.
- A natural shared seam for prepared input is after execution-contract validation in `prepare_worker_run` and before prompt/command creation (`18988-19014`). The same materialized artifact/reference can then be represented in the generated prompt and driver command/environment. Existing drivers do not currently expose a prepared-input placeholder.

## Driver command, files, and environment

- `tools/processforge.py:18177-18195`: supported placeholder allowlist includes project/processforge roots, run/task IDs, capsule/prompt/workspace-access/report/stdout/stderr/heartbeat/exit paths, model, reasoning, and sandbox. The allowlist is `RUNTIME_DRIVER_PLACEHOLDERS` (`18166-18182`); `driver_placeholder_errors` and `expand_runtime_value` reject unsupported names (`18317-18329`, `18563-18578`). Although `attempt` is included in the expansion variables and PF environment (`18709-18715`, `18371-18383`), `{attempt}` is not currently in the placeholder allowlist.
- `tools/processforge.py:18363-18391`: `build_worker_environment` records PF-owned run/task/attempt, project, driver, workspace-access, model/reasoning, agent-run and exit paths; configured environment values are expanded, reserved PF keys cannot be overridden, and host environment inheritance is deferred until launch. `18689-18787` expands driver executable/args/model args, records argv/working directory/environment/paths/limits in `command.json`, and sets `shell: false`.
- `templates/runtime-drivers/manual.yaml:1-9`: kind `manual`, creates prompt and capsule and explicitly does not start a process.
- `templates/runtime-drivers/generic-shell.yaml:1-35`: kind `shell`; executable is an explicit `{executable}` override, argv receives worker-prompt and capsule paths (not stdin), optional model args are appended; environment inherits by default; stdout/stderr and optional heartbeat use per-run/task paths; network is disabled; `max_retries` defaults to zero.
- `templates/runtime-drivers/codex-exec.yaml:1-39`: invokes `tools/codex_exec_worker.py` through Python and passes prompt, capsule, workspace-access, expected report and heartbeat paths. PF_CODEX sandbox/reasoning/memory values are passed through driver environment. Network is explicitly allowed with a reason.
- `tools/processforge.py:18994-19024` validates/constructs the durable command and attempt before start. Manual preparation sets `manual_required`; shell drivers set `ready` (`19014-19021`). The prepared launch state/command are persisted under `.pf/runtime/agent-runs/<run>/<task>/`.

## Codex wrapper and lifecycle

- `tools/codex_exec_worker.py:114-134`, `prompt_payload`: concatenates generated prompt, output-delivery instructions, full capsule text, and workspace-access file path. The workspace-access JSON itself is not inlined here.
- `tools/codex_exec_worker.py:137-211`, `capture_worker_input`: for a governed run/task/attempt, hashes the exact UTF-8 launch payload, writes `worker-input-contract.json` in the expected agent-run directory, then submits a private raw envelope and safe summary through Host ingress. Missing run/task is allowed only for the pre-existing direct CLI smoke path; if agent-run metadata is set, missing IDs fail closed.
- `tools/codex_exec_worker.py:234-302`: requires configured model, resolves granted workspace directories for `--add-dir`, constructs `codex exec ... -o <report> -`, writes `starting` heartbeat, captures input before launching, sends UTF-8 prompt bytes on stdin, then writes durable `exit.json` and completed/failed heartbeat. Codex MCP tool approval is enabled by `codex_config_args` (`57-68`); the worker expects the ProcessForge MCP service to be available, it does not bootstrap/register it itself.
- `tools/processforge.py:19046-19110`: start prevents duplicate active launches under lifecycle lock, launches with `shell=False`, records process/status, and supports detached or wait mode. `observe_worker_run` (`18889-18955`) reconciles heartbeat-independent durable exit proof after restart, otherwise uses process liveness/timeout and reports `unknown_exit` rather than assuming success.
- `tools/processforge.py:19157-19255`: collection accepts only `completed` or `manual_required`, requires configured outputs and report, hashes the report and emits an attempt-scoped output envelope, captures it through Host, then invokes task completion. This is distinct from worker launch and supports manual report collection.
- Attempts increment on each deliberate preparation (`19008-19014`); the previous exit contract is removed for the new attempt (`19017-19020`). `max_retries` is validated and persisted (`18333-18350`, `18829-18830`) but source search found no automatic retry consumer. Retry is therefore a new explicit prepare/start attempt, not driver-managed retry.

## Existing focused coverage

- `tools/smoke_codex_exec_worker.py:134-173,177-210`: real source worker-run start through fake Codex executable; checks argv, workspace grant directory, stdin payload including Cyrillic, output-delivery rules, model/effort, heartbeat/exit and missing-model failure.
- `tools/smoke_codex_worker_governance.py:17-96`: generated prompt MCP ordering, PF tool approval override, memory-off setting, Codex sandbox selection and managed-hook trust rejection for foreign hooks.
- `tools/smoke_worker_workspace_access.py:77-135`: capsule/public-reference privacy, manual prepare output, resolved private runtime grant, prompt boundary, command path and `PF_WORKSPACE_ACCESS_FILE`.
- `tools/smoke_runtime_driver_registry.py:18-91`: built-in manual/generic-shell/Codex registry, executable readiness, driver validation, invalid limits and reserved environment rejection.
- `tools/smoke_worker_run_shell.py:241-511`: launch environment isolation, stale capsule rejection, duplicate sequential/parallel start, no re-prepare while running, direct-path driver recovery, durable-exit reconciliation and collect.

## Mapping cautions

- Do not equate capsule, workspace-access metadata, generated prompt, and prepared input: they have different content/privacy roles. The Codex wrapper currently inlines the capsule but only references the workspace-access file.
- Generic shell has `stdin: none`; its current contract is prompt/capsule file arguments. A prepared-input addition needs an explicit common handoff usable by manual and generic-shell as well as Codex, without treating driver/model preference as permission.
- `max_retries` currently communicates a validated limit but does not itself retry. Durable attempt identity is already used in worker input/output capture, so reattempt behavior must preserve that distinction. Also, templates cannot currently interpolate `{attempt}` despite the variable being available internally; the placeholder allowlist would need to match any chosen attempt handoff.
- This is source-level mapping only; no test, launch, Work transition, or runtime state was created.


