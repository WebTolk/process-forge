# Heartbeat Contract Fix Report

- reproduced: `no` against the current checkout/archive
- exact failing command: `python tools/smoke_shell_launched_agents_supervisor_fix.py`
- observed current behavior: the command passed from a clean extraction of `dist/processforge.zip`
- heartbeat contract decision: `mandatory`
- exact heartbeat path: `.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`
- concrete proof path used by the assignment smoke: `.pf/runtime/agent-runs/agent-proof-run/proof-agent/heartbeat.json`

## Root Cause

The original missing-heartbeat failure was not reproducible in the current
`dist/processforge.zip`; clean extracted baseline checks passed. The fix still
closed confirmed contract gaps in the current code:

- shell runtime env relied on legacy explicit `PF_WORKER_RUN_ID` and `PF_WORKER_TASK_ID` rather than an injected canonical contract;
- `heartbeat_path` was not resolved from the runtime driver's `heartbeat.path` before argv expansion;
- `pf_shell_agent.py` wrote a heartbeat, but not the full mandatory machine-readable contract;
- the targeted supervisor smoke read `heartbeat.json` directly and could surface a bare `FileNotFoundError`.

## Changed Files

- `tools/processforge.py`
- `tools/test_agents/pf_shell_agent.py`
- `tools/smoke_shell_launched_agents_supervisor_fix.py`
- `tools/smoke_shell_agent_heartbeat_contract.py`
- `tools/smoke_full_shell_agents_supervisor.py`
- `templates/runtime-drivers/test-shell-agent.yaml`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `docs/concepts/process-supervisor.md`
- `docs/concepts/runtime-drivers.md`
- `docs/getting-started/runtime-driver-supervisor.md`
- `docs/ru/concepts/process-supervisor.md`
- `docs/ru/concepts/runtime-drivers.md`
- `docs/ru/getting-started/runtime-driver-supervisor.md`
- `docs/known-limitations.md`
- `docs/release-checklist.md`

## Compatibility

Keeping `heartbeat.json` mandatory is compatible with the previous shell-agent
proof acceptance because that acceptance already required:

- `process.json`
- `command.json`
- `stdout.log`
- `stderr.log`
- `heartbeat.json`
- `exit.json`
- report artifact

The new contract keeps the same artifact set and only makes the live heartbeat
identity explicit.

## Evidence

Baseline clean extracted archive:

```text
PASS: runtime driver registry smoke
PASS: worker-run shell smoke
PASS: shell-launched agents supervisor fix smoke
```

Targeted and supervisor checks:

```text
PASS: runtime driver registry smoke
PASS: worker-run shell smoke
PASS: shell-launched agents supervisor fix smoke
PASS: shell-agent heartbeat contract smoke
PASS: full shell agents supervisor smoke
PASS: process supervisor smoke
PASS: process supervisor tick smoke
PASS: process supervisor lifecycle smoke
```

Regression checks:

```text
PASS: resource authoring processes smoke
PASS: update framework read-only smoke checks passed.
PASS: update framework validation regression smoke checks passed.
PASS: ProcessForge structure and JSON Schema validation passed.
PASS: public cleanliness checks passed.
```

Release and archive checks:

```text
PASS: release-test --public --fail-fast, elapsed 214.68s
PASS: release-test --public, elapsed 207.24s
PASS: release-pack, FILES: 457
PASS: release-archive-test, extracted release-test elapsed 208.03s
PASS: clean extracted archive targeted smokes
PASS: clean extracted archive release-test --public --fail-fast
```

Clean extracted archive proof path:

```text
C:\Users\musst\AppData\Local\Temp\pf-heartbeat-final-c52f14f123ac461dada321b4d17cae6a
```

## Commands Run

```bash
python -m py_compile tools/processforge.py tools/test_agents/pf_shell_agent.py tools/smoke_shell_launched_agents_supervisor_fix.py tools/smoke_full_shell_agents_supervisor.py tools/smoke_shell_agent_heartbeat_contract.py tools/validate-process-forge-schemas.py tools/validate-public-cleanliness.py
python tools/smoke_runtime_driver_registry.py
python tools/smoke_worker_run_shell.py
python tools/smoke_shell_launched_agents_supervisor_fix.py
python tools/smoke_shell_agent_heartbeat_contract.py
python tools/smoke_full_shell_agents_supervisor.py
python tools/smoke_process_supervisor.py
python tools/smoke_process_supervisor_tick.py
python tools/smoke_process_supervisor_lifecycle.py
python -u tools/smoke_resource_authoring_processes.py
python -u tools/smoke_update_framework_readonly.py
python -u tools/smoke_update_framework_validation.py
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python tools/validate-process-forge-checksums.py --root . --write
python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1
python bin/pf.py release-test --root . --public --timeout-scale 1
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1
python tools/smoke_runtime_driver_registry.py
python tools/smoke_shell_launched_agents_supervisor_fix.py
python tools/smoke_shell_agent_heartbeat_contract.py
python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1
```

## Elapsed Time

- clean extracted baseline: about `24s`
- targeted heartbeat contract smoke: about `26s`
- full shell supervisor smoke after threshold adjustment: about `42s`
- regression smokes and validators before checksum refresh: about `19s`, `7s`, `10s`, `3s`, `2s`

## Remaining Limitations

- The original missing-heartbeat failure did not reproduce in the current archive; this fix hardens the contract and adds direct regression coverage.
- The clean extracted archive release-test reports a warning because it is not a Git checkout and skips `git diff --check`; this is expected for ZIP extraction.
