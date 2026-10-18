# Orchestration: evolve-20261002-01

Task: implement `evolve-20261002-01` so Work creation preflights execution mode and effective permissions before publishing Run, Assignment, or capsule.

Context:
- `pf.context` returned fresh snapshot `ctx-20261002-060156-86cbed` with `policy_action=continue`.
- Backlog assignment `evolve-20261002-01` is planning-only/read-only and blocked for product writes.
- Scoped successor Work was created with run `garage-implement-evolve-20261002-01-preflight-execution-mode-and-effecti`, assignment `implement-evolve-20261002-01-preflight-execution-mode-and-effective-perm`, capsule `sha256:c08da50de4bb98717fb4eb98f16d219ada930682b2fe82bb344518f74c9bb2ce`.
- Execution readiness is `ready`; writable scope is limited to `src/processforge_core/process_execution.py`, `src/processforge_core/continuation.py`, `tools/smoke_work_start_scope.py`, related docs, and this task's PF artifacts.

Lifecycle decision:
- Use `software-feature-development`.
- Execute the normal stages sequentially.
- Treat `tools/processforge.py` as read-only because active assignment `agent-entry-e01-e02-scoped` owns that file.
- Use PF-resolved Python documentation resources (`docs.python:root`, `docs.python-practices:root`) for Python-specific checks.

Immediate plan:
1. Investigate current preflight and permission readiness behavior.
2. Implement one Core pre-publication check that reports `created/ready/blocked` before durable Work publication.
3. Extend targeted smoke coverage for implicit implementation denial, explicit planning/read-write artifact success, read-only/docs-only/implementation, empty grants, contradictory denials, and timeout retry identity behavior where covered by current scope.
4. Update concise EN/RU documentation only where the executable contract changes.
