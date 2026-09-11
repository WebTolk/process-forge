# Run Summary: F09-F12 update integrity search and incremental ingress

- run_id: `core-f09-f12-shell-20260910`
- status: `completed`

## Tasks

- `f09-update`: `done` - Collected worker run output from codex-exec
- `f1011-search`: `done` - Primary accepted corrected implementation and four real search smokes; worker exited zero but collection transcript cardinality rejected.
- `f12-ingress`: `done` - Primary accepted corrected implementation and actual scaling crash concurrency corruption smokes; worker exited zero but collection transcript cardinality rejected.
- `f0912-review`: `done` - Independent bounded review PASS with limitations; primary accepted final fault delta. Worker exit zero, report cardinality collection failed, original report preserved.
