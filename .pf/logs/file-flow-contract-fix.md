# File Flow Contract Fix Log

## 2026-07-25 - orchestrator

- task: implement `.pf/artifacts/file-flow-fix-plan.md`
- shell agents launched: `schema-contract-agent`, `cli-lifecycle-agent`, `context-capsule-agent`, `runtime-hooks-agent`
- shell agent reports: `.pf/artifacts/file-flow-agents/*.md`
- product files changed: `tools/processforge.py`, schema files, runtime driver template, smoke tests, docs, process definition
- `.pf` files changed: run/task assignments, context snapshots, ADR, registry provider, reports/logs
- status: implementation complete; targeted validation and full `release-test --fail-fast` passed
- residual risk: process authoring companion docs/examples for `task-batch-execution` remain outside this slice

## 2026-07-25 - package rebuild

- task: rebuild `dist/processforge.zip` and `dist/processforge.manifest.json` from the current repository state
- files changed: `dist/processforge.zip`, `dist/processforge.manifest.json`, `.pf/logs/file-flow-contract-fix.md`
- status: package rebuilt
- verification: `python tools/processforge.py release-archive-test --archive dist/processforge.zip --manifest dist/processforge.manifest.json --root . --extracted-test quick` passed with 457 files

## 2026-07-25 - detached worker exit contract regression

- task: fix `tools/smoke_full_shell_agents_supervisor.py` failure where bounded supervisor polling could miss a failed detached worker and later infer success from an existing report artifact
- files changed: `tools/processforge.py`, `tools/test_agents/pf_shell_agent.py`, `tools/smoke_full_shell_agents_supervisor.py`, `schemas/agent-run-state.schema.json`, `.pf/logs/file-flow-contract-fix.md`
- contract change: `PF_AGENT_EXIT_PATH` is a reserved ProcessForge worker env var; contract-aware workers write `exit.json`; supervisor marks a lost detached worker without `exit.json` as `unknown_exit` instead of `completed`
- regression added: `bounded-fail-shell-run` starts a slow failing worker without an exit marker, stops after one supervisor tick, then verifies the next tick records `unknown_exit` and never converts the failed report into `completed`
- verification: `python -m py_compile tools/processforge.py tools/smoke_full_shell_agents_supervisor.py tools/test_agents/pf_shell_agent.py` passed
- verification: `python -u tools/smoke_full_shell_agents_supervisor.py` passed
- verification: `python tools/processforge.py release-test --root . --only smoke_full_shell_agents_supervisor --fail-fast` passed
- verification: `python tools/processforge.py release-test --root . --only smoke_shell_agent_heartbeat_contract --fail-fast` passed
- follow-up: `.pf/artifacts/checksum-inventory.sha256` refreshed with `python tools/validate-process-forge-checksums.py --root . --write`
- verification: `python tools/processforge.py release-test --root . --fail-fast` passed
- delivery: rebuilt `dist/processforge.zip` and `dist/processforge.manifest.json` with 457 files
- verification: `python tools/processforge.py release-archive-test --archive dist/processforge.zip --manifest dist/processforge.manifest.json --root . --extracted-test quick` passed
