# Private development delivery: journal replay, 2026-10-16

Status: accepted sources; exact cumulative archive/install/profile pending.
Internal development iteration of version 1.1.0; public 1.2.0 is not published.

The candidate includes accepted journal source `cd 6b 893574695f 73bf 37ea 3a 1471bddcfaa 00af 6` and service
publication source `83faf 5aebccd 55fd 3f 451889b 7dba 3e 656f 4c 36e`, with the previously installed
canonical Work selection, scope, prepared-YAML and diagnostics corrections.
See [journal audit](../audits/journal-error-row-replay-20261016.md) and
[service publication audit](../audits/runtime-service-publication-20261016.md).
Only new portable notes, readiness and a clean-candidate checksum are added here.

The new journal source preserves current whole-byte verification, first-match
and error ordering, the original guard/fsync/hooks and bounded private facts.
Five source batch pairs preserve exact bytes/results: four append median
5.197518 to 2.511963s, four read-only lookups 5.470902 to 1.866624s. Initial source
review failures and their correction proof remain explicit. Older installed Runtime was active; the last narrow native review admission
and preparation overlapped some source samples. These timings do not establish actual installed/Runtime improvement.

The last installed development baseline passed targeted diagnostics and two
original public time budgets, but its actual Runtime remained degraded and
used 94.824percent of one core in a separate 45s window. A new manifest-owned
single update, protected config/history and backup verification, quiet original
checks, normalCLI/fresh independentstdio and actual Runtime profile follow.
Actual connected-host proof and full 1.2version/changelog/migration/source/archive
suites remain separate. Stable publication requires a detailed report and
explicit approval. Broad smoke audit/cleanup is a later independent task.
