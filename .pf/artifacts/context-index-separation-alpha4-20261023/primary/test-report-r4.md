# Corrected final alpha4 assurance

Exact clean candidate: source-candidate-r15.json, 41 files.
Whole pytest on these bytes: `722 passed, 7 skipped, 246 subtests passed in 287.25s (0:04:47)`. All 15 affected native checks passed.
Actual CLI acceptance r4 passed seven real invocations, with the real schemas,
transactions, SQLite, successful-ID-only final pass, resumed known coverage,
unchanged unselected rows and separate explicit full reconciliation. This fixture
also registers a containment-denied template; its outside body remains unindexed.

The completed independent r13 review returned CODE NO-GO with four real defects.
Eight new regressions reproduced all four before correction. The regression file
now passes 50 cases, including unavailable/unresolved roots on an established DB,
verified read failure and explicit rebuild preserving the previous DB, empty-root
remapping and root addition without unselected body reads, and the actual composed
Main read race. A real strict-collection containment case preserves exclusion.
The immutable original/rejected r4/r10/r13 trees and all failed receipts remain.

Seven environment-dependent skips remain. There are 6 unclosed-SQLite
ResourceWarning records across stdout/stderr; on this run they appear at shutdown
rather than the pytest warning summary. They are not suppressed or claimed fixed,
and their collection location does not prove origin. Nine-new-module coverage:
statements 94.82%, branches 90.38%,
combined 93.97%; this is not whole-repository coverage.

Full native source and exact extracted archive release gates are still pending.
No installed device, actual connected host or native POSIX acceptance is claimed.
