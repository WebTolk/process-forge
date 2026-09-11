# R02 intake: clean release-candidate qualification

Date: 2026-09-11. Coordinator: primary agent.

Objective: qualify the current `dev` commit as a clean technical release candidate
by independently validating its source checkout, generated archive, and extracted
archive copy. This run does not publish a release, tag a version, update installed
Core, or modify the release version.

Starting point: `26353b517eb1b1d3fcd6e41fe9a88fbae8712e5e` is the local and
`origin/dev` head at intake. The source checkout contains active PF operational
state, so the candidate must be a detached clean worktree under `.pf/tmp/`.

Acceptance:

1. Candidate worktree is detached at the recorded commit and has no Git changes.
2. Source release checks pass in that candidate.
3. The archive has a recorded SHA-256 and passes source/archive parity checks.
4. Quick extracted-archive checks pass.
5. Results distinguish technical qualification from publication and installation.