# Private development delivery: collect and journal, 2026-10-16

Accepted cumulative source: `2930e6242f583ad8f51c7957b29fd6dcfb90a9da`. This private version 1.1.0
iteration includes bounded journal snapshots for multiple projects and explicit
recovery after stable semantic collect refusal. First/manual collection and a
new attempt retain full verification; successful capture remains historical
observation. Known transient errors still retry. Failed recovery stays visible.

See the [journal source audit](../audits/journal-multiproject-index-20261016.md)
and [collection source audit](../audits/supervisor-collect-recovery-20261016.md).
Source timings are separate from archive, installed Core and actual Runtime
qualification. The previous installed Runtime consumed 87.949% of one core in
a settled 45-second window. New startup and settled measurements follow after
one native manifest-controlled update and quiet installed checks.

The first two independent collector reviews found boolean/float coercion in
prepared, marker and receipt identity. Strict types, marker self-consistency
and independent re-signed document controls correct these findings. Both
failing reports are retained alongside the final independent review. Journal metadata
accounting is capped at 16 MiB, not RSS. Only CPython 3.14.3 has been executed in
this source slice; other supported interpreters need separate qualification.

Public 1.2.0 remains unpublished and requires a detailed report and explicit
approval. Full version/changelog/migration/source/archive checks and actual
connected-host acceptance remain ahead. Broad smoke cleanup and launcher
model policy are separate future tasks.
