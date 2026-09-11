# R01 intake: first-run project-profile search

Date: 2026-09-11. Primary coordinator.

Objective: establish whether a newly onboarded project must automatically make
its generated project profile searchable in Garage, then repair the violated
contract or the invalid test fixture with smallest scope.

Confirmed starting evidence:

- `smoke_user_like_garage_path` receives `empty_corpus` after normal
  `workplace-init` and `project-onboard`.
- The same failure was reproduced from baseline
  `901d0551773fe7a5b382b89ebe95b212b0747e83`; it is not an A01-A11 regression.
- Project initialization generates `.pf/artifacts/project-profile.md` and the
  project package declares `project-profile` as full-text. Context resolution,
  Garage root resolution and Workplace index registration disagree on whether
  that project-local resource reaches the index.

Scope: `tools/smoke_user_like_garage_path.py`, project-context construction,
Garage/search resolution, and a bounded read-only PF shell-worker diagnosis.
No installed-Core action, Runtime restart, release packaging, commit or public
release is part of this run.

Acceptance:

1. Reproduce the disposable first-run sequence and state the intended contract.
2. Preserve authorization boundaries and avoid snapshot-only index fixtures.
3. Add a regression only for confirmed intended behavior.
4. Use independent review after any implementation.
