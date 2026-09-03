# Multi-process implementation report

Status: ready_for_review

## Delivered Core changes

- Added a backward-compatible normalizer for legacy `process` and additive `processes.default`/`processes.allowed` selection.
- Added optional `process_id` to Core, CLI `work-start`, and the public `pf.work.start` MCP schema/handler.
- Added deterministic `process_not_found`, `process_not_allowed`, and `process_choice_required` responses with compact candidates.
- Pinned allowed processes, active specializations and selected resource identities alongside the existing process/snapshot fingerprint in Run, Assignment and the immutable capsule.
- Kept `pf.context` compact: it returns a default and ids for allowed processes, without process definitions.
- Exposed only active Work specializations/resources from `pf.work.state`.
- Added a completion advisory (`next` and `session_continuity`) without auto-starting sessions or Runs.
- Preserved the sessionless Garage path and the existing legacy fallback, including generic projects with no explicit process resource profile.

## Focused evidence

- `python -m py_compile` passed for all changed Python modules.
- Legacy context diagnostic returned `STATUS: fresh` after restoring the implicit-fallback boundary.
- Existing sessionless, session-bound, and declarative-stage smoke tests passed.
- A temporary three-process end-to-end fixture passed selection, denial, capsule pinning, completion recommendation and a separate next Run.

## Scope decision

No official `architecture-analysis` process was added: the short custom acceptance fixture proves the selection model without enlarging the 1.1.0 built-in catalogue. Manifest/schema/documentation and durable smoke integration remain the next bounded tasks.
