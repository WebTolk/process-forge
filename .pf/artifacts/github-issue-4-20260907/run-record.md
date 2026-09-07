# Run Record: GitHub Issue #4 Workplace migration

Status: draft

Objective: implement a compatible migration of an existing Workplace during the
ProcessForge 1.0.2 to 1.1.0 updater transition without replacing user-owned
configuration.

Scope:

- examine the published Issue #4 acceptance requirements and the current Core
  updater / Workplace initializer boundaries;
- add a plan-first, confirmed migration that installs missing PF-owned
  Workplace defaults such as `codex-exec`, preserves existing values, and
  records recovery information;
- add an isolated 1.0.2-to-1.1.0 Workplace acceptance smoke and update the
  affected operator documentation;
- run focused smoke tests and the relevant ProcessForge validation gates.

Intake evidence:

- Issue #4 was read from the authoritative GitHub repository on 2026-09-07;
  it is open and has no comments.
- The current Core updater updates only the Core archive. The existing
  `workplace-init --apply` flow is an initializer and can propose unrelated
  `.candidate` files, so it is not an acceptable migration path.
- A fresh project context was generated before continuing this governed run.

Boundary:

- Existing uncommitted changes outside this Issue #4 implementation are owned
  by another workstream and must be preserved.
- No update will be applied to an installed Core or real Workplace during this
  development run. All apply and rollback evidence will use isolated fixtures.
