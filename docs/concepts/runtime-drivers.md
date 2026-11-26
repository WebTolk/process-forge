# Runtime Drivers

Runtime drivers describe how ProcessForge may prepare or start a worker task.
They are optional. The default driver is `manual`, which writes launch material
and requires a human or external workplace to run the task.

Built-in drivers:

- `manual`: prepares state and never starts a process.
- `generic-shell`: starts an explicit executable with configured arguments.
- `codex-exec`: starts a Codex CLI worker with verified prepared input.
- `test-echo-worker`: local smoke-test worker that writes the expected report.
- `test-shell-agent`: local smoke-test shell agent that writes report,
  stdout/stderr, process, heartbeat, and exit proof artifacts.

Driver manifests live under `templates/runtime-drivers/`. The built-in registry
is `templates/registries/runtime-drivers.yaml`. A project may add local registry
overrides under `.pf/runtime/registries/runtime-drivers.local.yaml`.

Use the CLI from an onboarded project. A primary agent can work directly
through the CLI or MCP. Select a runtime driver for an assignment that needs a
separate worker. Model selection is optional. Request a catalog with
`runtime-driver describe --project-root . --driver <driver-id> --catalog`.
`unsupported` means the driver offers no catalog. A driver reporting `unknown`
could not read its catalog.

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver describe --project-root . --driver test-echo-worker
```

Driver placeholders are restricted to runtime facts such as `{project_root}`,
`{run_id}`, `{task_id}`, `{agent_run_dir}`, `{driver_id}`,
`{capsule_path}`, `{worker_prompt_path}`, `{workspace_access_path}`,
`{expected_report_path}`, `{stdout_path}`, `{stderr_path}`,
`{heartbeat_path}`, `{exit_path}`, `{agent_model}`, and
`{agent_reasoning_effort}`.
Unknown placeholders fail validation.

ProcessForge always injects reserved worker environment variables including
`PF_RUN_ID`, `PF_TASK_ID`, `PF_AGENT_RUN_DIR`, `PF_AGENT_EXIT_PATH`,
`PF_AGENT_MODEL`, `PF_PROJECT_ROOT`, `PF_RUNTIME_DRIVER_ID`,
`PF_AGENT_REASONING_EFFORT`, `PF_WORKSPACE_ACCESS_FILE`, `PF_WORKER_RUN_ID`,
`PF_WORKER_TASK_ID`, `PF_WORKER_ATTEMPT`, `PF_PREPARED_INPUT_FILE`, and
`PF_PREPARED_INPUT_SHA256`. Shell drivers cannot override those names. A detached
contract-aware worker should write its final marker to `PF_AGENT_EXIT_PATH`;
if the supervisor later observes a lost process without that marker, it records
`unknown_exit` instead of inferring success from a report artifact.

When a shell worker has an agent model, ProcessForge exposes it as
`PF_AGENT_MODEL` and `{agent_model}`. If the driver command does not define
`model_args`, ProcessForge appends `--model {agent_model}` only when the model
is non-empty.

## Prepared execution and collection

Worker preparation requires a ready [execution contract](work-context.md),
an explicit expected report and matching write scope. It publishes a bounded,
immutable [prepared input](prepared-input.md) for one attempt. A primary Work
without these worker declarations is not worker-ready. The manifest carries
authorized resources and checked source references; it cannot widen permission.

`manual` prepares this input without launching a process. `generic-shell` uses
`tools/prepared_executor.py` to verify it, execute the configured argv, and record
heartbeat and exit state. `codex-exec` uses its existing wrapper with the same
verified manifest. Prepared execution can run without MCP; the executable's
actual network/filesystem access still depends on its operating-system sandbox.

Starting a ready worker reuses its prepared attempt. A changed preference or
blocked attempt requires explicit preparation again. Collection checks output
attribution and writes a receipt; repetition and dead-owner recovery must not
duplicate completion events. Governed collection records the result while the
primary Work stays on its current stage. The primary agent reviews evidence and
calls `pf.work.transition` to advance the process.

For governed Work, native prepare/start reject terminal assignments
(`done`, `completed`, `failed`, `cancelled`) and runs (`completed`, `failed`,
`cancelled`) with `work_is_terminal` before preparation or provider launch.
Direct native preparation also checks this before launch-preference writes.
Pending cancellation recovery keeps its existing priority. Reading status and
collecting an existing result remain available.

A failed worker attempt is separate from the governed Work lifecycle: supervision
retains the attempt failure without marking the assignment failed. An active,
ready Work can be prepared for another attempt; an already terminal Work needs a
separate successor. Supported legacy retries are preserved, including the existing
legacy rejection of `cancelled` tasks.

## Codex Exec

`codex-exec` is the built-in driver for launching shell-agents through the
Codex CLI. The driver runs `tools/codex_exec_worker.py`, which verifies the
prepared input path, checksum and identity before passing fixed instructions
and that manifest to Codex. In prepared mode it does not reread the mutable
worker prompt, capsule body or workspace-access pointer.

Run `pf runtime-driver describe --driver codex-exec --catalog --project-root <path>`
or call `pf.runtime_driver.describe` with `catalog: true` to read the configured
Codex model catalog. Each model reports its supported reasoning efforts and its
recommended effort. `configured_defaults` reports the effective Codex profile
separately. A confirmed empty list means the model offers no effort options.
A null list means Codex did not provide the options. If the catalog cannot be
read, its status is `unknown`. These calls read live data on Windows and Linux.

A worker can specify the model with `agent_model`, `--model`, plan-level
`runtime.model`, or worker-level `model`. `PF_CODEX_MODEL` provides an operator
override when `PF_AGENT_MODEL` is empty. When no model override is set, Codex
chooses the model from its profile.

Prepare and start use the configured Codex catalog to check the selected model
and its reasoning effort. If only the effort is set, PF checks it against the
effective Codex model. The wrapper forwards the chosen value as
`-c model_reasoning_effort="<value>"`. With no effort override, Codex uses its
own settings. The CLI and MCP return a diagnostic if an explicit selection
cannot be confirmed. Restarting preparation or start reads the live catalog
again.

Access to knowledge resources, templates and tools is resolved privately at
runtime. Public assignments and capsules may contain resource ids or `path_ref`
values, but private absolute
paths remain in private runtime files such as `workspace-access.json` and the
attempt's prepared manifest. The legacy direct wrapper can read workspace
access and use `--add-dir`; a prepared launch does not grant broad directories
from that file. Metadata-only grants never authorize resource body reads.

## Access to MCP tools

Actual MCP connections and tool approvals belong to each coding agent's own
configuration. PF's `workspace_access.mcp` declarations are advisory metadata;
they neither grant host-tool access nor control connection availability.
Preparation retains the normalized immutable declarations in
`input.resources.requested.mcp` and leaves `input.resources.grants.mcp` empty.
It does not resolve or pin MCP connections, check their revocation or probe
availability, and changes no agent configuration file or running MCP server.
Knowledge, template and tool resource checks, capsule and required-source
validation, and file/action scope and filesystem checks remain in force.
This compatibility behavior does not remove MCP fields or catalogs; that is
separate future work.

## Running a worker

For a first execution check, choose an assignment that declares an expected
report and grants write access to that path. Use its returned assignment ID.
The bundled test driver writes the report locally and needs no model account.

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task <assignment-id> --driver test-echo-worker
python .pf/runtime/bin/pf.py worker-run start --project-root . --task <assignment-id> --driver test-echo-worker
python .pf/runtime/bin/pf.py worker-run status --project-root . --task <assignment-id>
```

For an external CLI, select a registered driver configured for its executable
and arguments. A shell plan can set `runtime.default_driver`, `runtime.model`
and `runtime.reasoning_effort`. Individual workers can override model and effort.
`orchestrator-shell-plan-apply --model <model>` applies a model override to the
plan. Supply model or effort only when supported by the driver. [Worker collection and supervision](../getting-started/runtime-driver-supervisor.md)

Shell execution uses `shell=False`. Each driver declares its network needs.
The operating system or sandbox enforces any network isolation.

ProcessForge does not install agents, create agent folders, or require a daemon
for driver registry use.
