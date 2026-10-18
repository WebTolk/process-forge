# R02 task index and execution plan

The single governed R02 assignment is executed sequentially by the coordinator:

1. Build a detached Git worktree at intake commit under `.pf/tmp/r02-candidate` and prove it is clean.
2. Run the source release suite in the candidate. Capture terminal output.
3. Package the candidate, capture archive SHA-256 and inspect its release markers.
4. Run archive/source parity and quick extracted checks.
5. Obtain an independent bounded shell-worker review of packaging command boundaries and compare it with terminal evidence.
6. Perform coordinator review and close with a handoff that separates technical qualification from publication, tag, or installed-Core update.

The shell worker owns only `.pf/artifacts/r02-release-candidate-20260911/r02-release-command-review/**` and has no source-write permission. The primary agent owns candidate construction, package commands, validation evidence, and final integration.