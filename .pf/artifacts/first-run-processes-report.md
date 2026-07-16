# First-Run Processes Report

## Status

ready_for_review

## Implemented

- Added first-run CLI surface: `workplace-init`, `project-onboard`, `agent-start-prompt`, and `first-run`.
- Kept compatibility commands: `init-workplace` and `init-project`.
- Added `project-onboarding` as a separate process definition.
- Marked `workplace-initialization` as a first-run workplace process.
- Added project onboarding generation for `.pf/START_AGENT_HERE.md`, `.pf/assignments/first-assignment.yaml`, onboarding report, review, handoff, and project context snapshot.
- Added first-run event emission for workplace and project onboarding.
- Added first-run prompts, quickstart docs, examples, wrappers, and smoke test.

## Commands Added

- `python tools/processforge.py workplace-init --workplace <workplace-root> --apply`
- `python tools/processforge.py project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --apply`
- `python tools/processforge.py agent-start-prompt --project-root <project-root>`
- `python tools/processforge.py first-run --workplace <workplace-root> --project-root <project-root> --type <project-type> --apply`

## Process Definitions Added

- `processes/project-onboarding.yaml`

## Prompt Files Added

- `prompts/workplace-initialization-agent.md`
- `prompts/project-onboarding-agent.md`

## Workplace And Project Separation

`workplace-init` creates workplace files, registries, base folders, and workplace runtime events. It does not create project `.pf/`.

`project-onboard` requires an existing workplace, creates only the project-local `.pf/`, refreshes project context, creates the first assignment, and writes `START_AGENT_HERE.md`. It does not recreate the workplace or copy global packages into the project.

## START_AGENT_HERE

`.pf/START_AGENT_HERE.md` tells the next agent to read `.pf/AGENTS.md`, the project context snapshot, and the active assignment before running `doctor-project`.

## Tests Passed

- `python -m py_compile tools/processforge.py`
- `python tools/processforge.py --help`
- `python tools/smoke_first_run.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/smoke_resource_management.py`
- `python tools/validate-process-forge-checksums.py --root . --check`
- separate temporary `doctor-workplace` and `doctor-project` first-run check

## Limitations

- Wrappers are thin launchers and assume `python` is available on PATH.
- `--interactive` is accepted for first-run UX but remains non-prompting in this file-only MVP.
- `first-run` is only a convenience sequence, not a separate process definition.
