# Dev archive assurance: PASS

Clean source commit 48985ffae9130d09e72ac8c9fd8e908cbb41aa3a, version
1.3.0-alpha1. Only shipped checksum inventory changed for this release; accepted
accounting product bytes are unchanged. Earlier independent review/re-review and
registered Ruff/mypy evidence remain applicable. Clean candidate reran all 68
usage tests plus 36 subtests and four existing source smokes: Codex worker,
worker governance, MCP Codex contract and Core-update manifest; all PASS.

Schema, public cleanliness, checksum and release-check passed. Native archive-test
verified exact source/archive parity, safe members and per-file hashes, both CLI
entrypoints and the quick extracted suite (compile, schemas, cleanliness, checksum,
Core bootstrap, ingress, conversation completeness and replay). Result PASS.
This is bounded dev qualification, not a full stable/public release-suite claim.

Archive has 1477 entries; sha256
f689b41d4a67d14d68d94d974c7e648c224841af1acd07e2d9f7242af0701d71.
Read-only update plan: added=14, changed=9, unchanged=1453, removed=0,
missing_owned=0, locally_modified=0 and no blockers. Existing accounting SQLite
integrity is ok; configuration fingerprints and a native SQLite backup retained
privately. PF App Server stopped gracefully, with no force or child termination.

Proceed to one authorized Core apply, then verify installed hashes, preservation,
installed feature behavior, updater/workplace health and new App Server process.
Actual connected-MCP host provenance is a separate evidence layer.
