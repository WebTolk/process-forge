# Execution Context Prompt

You are working inside ProcessForge.

Read:

- root `AGENTS.md` (explicit `.pf/AGENTS.md` fallback for an unmigrated project)
- `.pf/process-forge.yaml`
- the supplied assignment and its pinned immutable capsule or Execution Context Package
- required sources and authorized resources selected for this Work

Use the supplied or returned Run/assignment/capsule identities, not an unrelated
assignment from an old report. Primary agents verify `pf.context`, resume exact
existing Work through `pf.continuation.status` and `pf.continuation.resume`, or
use `pf.work.start` for new work, then `pf.work.state` and `pf.work.transition`
to `run_completed`. Without a bound session, pass returned exact selectors to
every Work call. Use `pf.work.search` and `pf.work.resolve` for its resources.
A bounded worker follows its supplied contract and must not reselect or rebuild it.
Read extended `.pf/AGENTS.md` instructions on demand; START is not authority.

Prepared workers use only their immutable input, inline sources and declared
file references. Metadata-only grants do not authorize body reads. No PF MCP
connection is required. Follow the supplied output delivery contract.

Respect allowed files, forbidden files, required outputs, quality gates, and handoff requirements.

Do not edit outside the assignment scope without a handoff.

Keep repository scratch in your own `.pf/tmp/` directory only when writes are
allowed. Do not install, start, restart or repair PF infrastructure.
