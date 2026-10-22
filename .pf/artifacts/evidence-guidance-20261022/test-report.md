# Test report

2026-10-22. PASS on a clean public snapshot of base
be1af5cba8412eaa5bb8b1f96d156a3bc23214e8 plus exactly six scoped source/docs
overrides and the new test directory. Unrelated WIP excluded.

- 65 pytest cases passed, including real source CLI/ordinary stdio MCP parity,
  immutable pin drift, invalid request/no assignment write, negative matching and
  valid retry, source cycle to run_completed, blocked scope, conditional entry gate.
- Seven existing smoke scripts passed: current-stage state, missing gate, linear
  transition, evidence recording, invalid-evidence recovery, pinned process,
  evidence identity/file freshness.
- Every generated example is checked against the existing normalizer/matcher.
  Source matcher/normalizer acceptance rules remain unchanged. Stored hash/file
  failures are not fixed by guidance; a supplied hash is still recomputed by PF.

Initial fixture failures were corrected in tests: provide explicit scope at
creation, request CLI JSON explicitly, and pass exact selectors for terminal Work.
No product acceptance relaxation was made to accommodate the fixtures.

Raw local evidence: clean-verification.json and clean-*.log in this artifact
directory. The scoped clean-source snapshot and its build/verification scripts
are retained under task tmp as reproducible source-validation evidence.

Limits: source CLI and independent stdio MCP only. No release ZIP, installed Core,
actual connected host, browser UI, infrastructure update or restart qualification.
