# Work admission scope latency — 2026-10-15

The measured admission bottleneck was the scope-overlap algorithm. One profiled
native admission took 608.553 seconds, of which scope validation took 590.723
seconds (97.07%). A later, different task took 291.740 seconds before this repair.
These observations use different scopes and are not a repeated benchmark.

`ScopeConflictService` now owns comparisons for admission, supervisor ticks and
orchestrator plan validation. Different mandatory literal prefixes can prove
that two globs cannot overlap. Such pairs, exact paths and identical globs need
no file inventory. Unresolved glob pairs share one lazy, normalized inventory
per operation. Assignment records still load on every validation. There is no
cross-operation cache.

Conflict fields, reasons, ordering, forbidden scope precedence, dependencies,
verified predecessor handoffs and the existing eligible-file traversal remain
unchanged. In particular, an existing shared file still produces
`glob_matches_same_file` before the conservative `possible_glob_overlap` fallback.
Locking, recovery, public CLI/MCP contracts and policy overrides are unchanged.

## Measurements

Five before and five after samples per scenario used the same controlled tree
of 2,004 files and the same ordered scope lists. Timings include inventory and
comparison, excluding interpreter startup/imports. All output hashes match.

| Scenario | Before median | After median |
| --- | ---: | ---: |
| 240 disjoint glob pairs | 3.052751 s | 0.001154 s |
| Shared literal prefixes | 0.300242 s | 0.196319 s |
| Empty literal prefixes | 0.270876 s | 0.247330 s |
| Exact paths and globs | 0.143903 s | 0.000068 s |

Five read-only validations of the current admitted task against 855 actual
assignment records took 1.628–3.287 seconds, median 1.782 seconds. A separate
cProfile run observed no inventory call. This measures scope validation, not a
complete new Work admission or the installed Core.

## Qualification boundaries

The existing scope smoke now covers 484 baseline pattern pairs, exact reasons
and conflict order, unnecessary traversal, per-operation inventory reuse,
inter-operation file and assignment changes, forbidden precedence, dependencies,
inactive/malformed records and existing native CLI/handoff/retry controls.
Directory-symlink qualification is skipped when the host cannot create one.
Focused source and exact archive receipts belong to the governed task report.

Ambiguous globs can still require a whole-tree inventory. Catalog/YAML loading
remains a separate source of latency. These results do not establish universal
subsecond admission or installed/Runtime/connected-host acceptance. Device
qualification follows a separately governed development release.
