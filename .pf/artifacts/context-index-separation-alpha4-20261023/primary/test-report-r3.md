# Final alpha4 source assurance

Final clean candidate: source-candidate-r13.json, 41 public files.
Whole pytest with branch instrumentation on r12: `713 passed, 7 skipped, 6 warnings, 246 subtests passed in 290.29s (0:04:50)`.
The only r13 changes are import-group whitespace in one test and one smoke, plus
their inventory hashes. All production bytes and every Python AST are identical;
r12 tested bytes are retained. r12-r13-parity.json binds that proof. No r13 whole
pytest run is invented. All 15 affected native checks passed, including the fixed
fixture MCP/readiness smoke and unchanged transactional-authoring assertions.

Actual CLI acceptance passed seven invocations with the real bundled schemas,
native per-item transactions and SQLite. Dry-run leaves all workplace bytes
unchanged; mixed results remain ordered; one selected writer attempt receives
only successful qualified IDs. Known complete coverage resumes search without
reading unselected bodies. A later explicit full pass updates the intentionally
unselected document. URL defaults index metadata without downloading.

The regression suite covers independent-review defects, source read/scan refusal,
durable publication/identity and query races, scoped counts, unknown/known/mixed
notifications, token/retirement failure, prior failure recovery, metadata drift,
disabled rows and private metadata filtering. The native batch contributor added
31 behavioral tests, including real native manifest/index/private-registry and
audit recovery fixtures. Twelve real indexing-schema cases validate the exact
bundled ref, internal definitions, malformed/missing data and refusal of other
external refs. Existing native search/readiness assertions were preserved.

Seven environment-dependent skips and six existing SQLite ResourceWarnings remain;
the varying collection locations do not prove their origin. No warnings were
suppressed and no warning fix is claimed. Nine-new-module coverage: statements
94.67%, branches 89.74%, combined
93.73%. The whole instrumented denominator is reported
separately and is not whole-repository coverage.

Historical failed/rejected QA/native attempts and original r4/r10 trees remain
retained. Source full native release qualification and exact consumer archive
qualification are still pending. No installed-device, actual connected-host or
native POSIX acceptance is claimed.
