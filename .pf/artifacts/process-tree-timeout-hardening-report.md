# Process Tree Timeout Hardening Report

## Scope

Implemented `задания/processforge_process_tree_timeout_hardening_master_prompt.md`.

## Problem

`release-test` and smoke scripts previously used direct `subprocess.run(..., timeout=...)`. That applies a timeout to the immediate child process, but it is not a durable process-tree cleanup policy for nested child processes and can leave ambiguous pipe diagnostics on timeout.

## Unified Helper

Added `tools/processforge_subprocess.py` with:

- `CommandResult`
- `run_command()`
- `tail_text()`
- `diagnostic_text()`

The helper starts commands without `shell=True`, captures stdout and stderr separately, applies a timeout, and returns structured timeout state.

## Process Tree Cleanup

On POSIX, commands run in a new session and timeout cleanup terminates the process group before escalating to a kill signal.

On Windows, commands run in a new process group and timeout cleanup uses direct process termination with a safe tree cleanup attempt through the operating-system task termination utility. No product daemon, watcher, scheduler, or runner was added.

## Updated Callers

Updated:

- `tools/processforge.py` release command runner
- `tools/processforge.py release-archive-test`
- `tools/smoke_first_run.py`
- `tools/smoke_resource_management.py`
- `tools/smoke_resource_authoring_processes.py`
- `tools/smoke_process_run_task_batch.py`

Direct `subprocess.run`, `subprocess.call`, and non-helper `subprocess.Popen` calls are no longer present in release-test or smoke scripts.

## Launcher Check

The generated project-local launcher now resolves the project root from the launcher path when it is executed by absolute path from another current directory. `smoke_first_run.py` covers this case.

## Validation So Far

Passed:

- `python -m py_compile tools\processforge_subprocess.py tools\processforge.py bin\pf.py tools\smoke_first_run.py tools\smoke_resource_management.py tools\smoke_resource_authoring_processes.py tools\smoke_process_run_task_batch.py`
- `python tools\smoke_first_run.py`
- `python tools\smoke_resource_management.py`
- `python tools\smoke_resource_authoring_processes.py`
- `python tools\smoke_process_run_task_batch.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root . --check`
- `python tools\processforge.py release-check --root .`
- `python tools\processforge.py events-validate --project-root .`
- `python tools\processforge.py release-test --root .`
- `python tools\processforge.py release-pack --root . --output dist\processforge-v0.1.0.zip`
- `python tools\processforge.py release-archive-test --archive dist\processforge-v0.1.0.zip`
- `python tools\processforge.py doctor-project --project-root .`
- `git diff --check`

`doctor-project` reported only known non-blocking WARN entries for this repository's self-dogfooding state.

## Remaining Limits

This is reliability hardening only. It does not add Process Authoring MVP, multi-agent leases, background execution, live hook interception, network webhook sending, GUI, marketplace, or database behavior.
