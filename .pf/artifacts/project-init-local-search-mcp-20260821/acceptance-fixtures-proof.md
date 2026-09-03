# Acceptance proof: initialization, repair, search, and session context

Status: pass.

The isolated executable fixture is `tools/smoke_project_init_acceptance.py`.
It creates its workplace and project only in a system temporary directory.

Verified in one successful run on 2026-08-21:

- A clean `project-onboard --apply` with explicit `--platform`,
  `--specialization`, and `--process` persisted all three bindings.  The
  command returned success only after `doctor-project` reported `pass`, and
  `project-init-status` reported `complete`.
- Deleting the deterministic `START_AGENT_HERE.md` made initialization
  `repairable`. `project-init-repair --repair-action
  restore_deterministic_artifacts --apply` restored it without overwriting a
  separate semantic user artifact, without a duplicate candidate, and
  returned the state to `complete`.
- Snapshot-authorized SQLite FTS5 returned `empty`, then performed the
  expected `stale` rebuild followed by `current`; a controlled SQLite failure
  returned the stable `search_unavailable` error.
- An authenticated Ledger session observed the real PF transition from
  `architecture-plan` to `implementation`. Its `pf.session_context` payload
  changed both `work.stage_id` and `work.stage_obligations.stage_id`.

Command:

```powershell
python tools/smoke_project_init_acceptance.py
```

Observed terminal result:

```text
PASS: project initialization, repair, FTS5 lifecycle, and session obligation acceptance smoke
```

Residual scope: this fixture does not claim live Codex UI/MCP visibility or
release/archive validation; those are independent gates.
