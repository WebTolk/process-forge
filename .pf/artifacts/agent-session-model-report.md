# Agent Session Role Model Report

Date: 2026-07-26

## Scope

Implemented the ProcessForge single-agent session role model from
`задания/processforge_single_agent_session_role_model_master_prompt.md`.

The delivered model defines the atomic unit as:

- one operator
- one primary agent session
- one project
- one active process or run

## Delivered Behavior

- `agent_id` presence is now session-safe: active records are stored under
  `runtime/agent-presence/<agent-id>/<session-id>.json`.
- One `agent_id` can have multiple simultaneous `session_id` records across
  projects or shells.
- `agent-checkin` auto-generates a session id when omitted, prints it, supports
  `--json`, and writes current-session references for project-local lookup.
- `agent-heartbeat` and `agent-checkout` can resolve the active project session
  from `--project-root` without manually passing `--agent` or `--session`.
- `session-start`, `session-heartbeat`, `session-end`, and `session-status`
  are available as the human-facing session commands.
- Existing telemetry-style `session-start --mode ...` remains available when
  no `--agent` is passed.
- `agent-status` supports filtering by agent, session, project id, and
  project root.
- `agent-availability` can resolve project context from `--project-root`.

## Process And Documentation

- Added EN/RU concept docs for the agent session model.
- Updated README, Quickstart, concept docs, getting-started docs, release
  checklist, prompts, process definitions, and process authoring schema/template.
- Added `execution_mode` choices for process authoring:
  `single_agent`, `single_agent_with_subagents`, `orchestrated_agents`,
  `process_factory`.
- Updated process authoring so pure `single_agent` flow does not ask for
  Director, Supervisor, route, lease, handoff, or external-worker design unless
  the selected mode requires them.
- Clarified that Agent Ledger is CLI/file state, not an agent.
- Clarified that Director and Supervisor/Execution Inspector are optional roles
  for multi-session, process-transition, or external runtime worker scenarios.

## Tests Added

- `tools/smoke_single_agent_session_flow.py`
- `tools/smoke_multi_project_agent_sessions.py`
- `tools/smoke_multi_agent_as_composed_sessions.py`

All three smokes are registered in the public release-test suite.

## Verification

Passed:

- `python -m py_compile tools\processforge.py tools\smoke_single_agent_session_flow.py tools\smoke_multi_project_agent_sessions.py tools\smoke_multi_agent_as_composed_sessions.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root . --write`
- `python tools\validate-process-forge-checksums.py --root . --check`
- `python bin\pf.py release-test --root . --only smoke_single_agent_session_flow --public --fail-fast --timeout-scale 1`
- `python bin\pf.py release-test --root . --only smoke_multi_project_agent_sessions --public --fail-fast --timeout-scale 1`
- `python bin\pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin\pf.py release-test --root . --public --timeout-scale 1`
- `python bin\pf.py release-pack --root . --output dist\processforge.zip`
- `python bin\pf.py release-archive-test --archive dist\processforge.zip --root . --extracted-test full --timeout-scale 1`
- Extracted archive direct checks:
  - `tools\smoke_single_agent_session_flow.py`
  - `tools\smoke_multi_project_agent_sessions.py`
  - `bin\pf.py release-test --root <extracted> --public --fail-fast --timeout-scale 1`

Archive result:

- `dist/processforge.zip`
- `dist/processforge.manifest.json`
- manifest files: 489
- extracted proof root:
  `C:\Users\musst\AppData\Local\Temp\pf-agent-session-final-8cf6eee73bc242c98957d4fbac8928dc`

The extracted public gate returned `PASS with warnings` only because
`git diff --check` is skipped in the temporary extracted directory, which is not
a git repository.

## Residual Risk

- Legacy `runtime/agent-presence/<agent-id>.json` records are still read for
  compatibility but new writes use the session-safe path.
- This task did not request or perform a git commit/push.
