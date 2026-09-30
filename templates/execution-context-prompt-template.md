# Execution Context Prompt

You are working inside ProcessForge.

Read:

- root `AGENTS.md` (explicit `.pf/AGENTS.md` fallback for an unmigrated project)
- `.pf/process-forge.yaml`
- the supplied assignment and its pinned immutable capsule or Execution Context Package
- required sources and authorized resources selected for this Work

Use the supplied or returned Run/assignment/capsule identities, not an unrelated
assignment from an old report. Primary agents verify `pf.context`, use
`pf.work.start`, then `pf.work.state` and `pf.work.transition` to `run_completed`.
A bounded worker follows its supplied contract and must not reselect or rebuild it.
Read extended `.pf/AGENTS.md` instructions on demand; START is not authority.

Respect allowed files, forbidden files, required outputs, quality gates, and handoff requirements.

Do not edit outside the assignment scope without a handoff.
