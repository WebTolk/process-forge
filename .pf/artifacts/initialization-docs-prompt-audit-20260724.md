# Initialization Docs And Prompt Examples Audit

Date: 2026-07-24 11:33 +04:00
Agent: codex-doc-auditor

## Scope

Checked documentation and prompt examples for ProcessForge initialization
surfaces:

- `first-run`
- `workplace-init` / `init-workplace`
- `workplace-setup start/review/apply/status`
- `project-onboard` / `init-project`
- project-local runtime use after onboarding
- multi-agent initialization of runs, assignments, capsules, and worker launch
  prompts

Primary files reviewed:

- `README.md`, `README.ru.md`
- `QUICKSTART.md`, `QUICKSTART.ru.md`
- `docs/getting-started/*`
- `docs/ru/getting-started/*`
- `docs/concepts/project-init.md`
- `docs/concepts/workplace-init.md`
- `docs/authoring/project-initialization.md`
- `prompts/*`
- `templates/*prompt*.md`
- `examples/first-run/*`
- `examples/processforge-init/*`
- `examples/guided-workplace-setup/*`
- `examples/multi-agent-orchestration/*`

## Confirmed Findings

1. `docs/getting-started/first-run.md` described two separate processes while
   listing the optional guided setup flow in the same list. The page now
   separates the two operational initialization processes from the optional
   preflight agent flow.

2. `docs/getting-started/agent-prompts.md` and
   `docs/ru/getting-started/agent-prompts.md` had a reusable prompt rule saying
   not to embed release numbers, but the same runbook used versioned archive
   names. The runbook now uses neutral archive filenames and leaves
   release-specific names to release checklists.

3. The agent runbook named `workplace-setup` and `first-run` but did not include
   complete command blocks for those initialization paths. Both English and
   Russian runbooks now include guided setup and first-run command examples.

4. The multi-agent minimal example mixed a project-local runtime launcher with
   an `--answers` path relative to the ProcessForge distribution. The example
   now runs from the distribution root and points `--project-root` at an
   onboarded project. Quickstarts now explain both contexts.

5. Project initialization docs did not state the important dry-run boundary:
   `project-onboard --dry-run` inspects the target project directory before
   writing, while apply mode can create a missing greenfield project root. The
   authoring docs, concept docs, quickstarts, and init examples now state this.

6. `docs/ru/getting-started/guided-workplace-setup.md` still had an English
   generated agent instruction snippet and English-heavy block names. The agent
   snippet and dialogue block descriptions are now Russian while preserving exact
   identifiers and commands.

## Residual Risks

- CLI behavior for `project-onboard --dry-run` on a missing project root is
  documentation-only in this slice. The implementation still reaches project
  inspection before any write path, so the documented requirement is intentional.
- Release-specific docs can still contain versioned archive names by design.
  Reusable prompt/runbook files should stay neutral.
