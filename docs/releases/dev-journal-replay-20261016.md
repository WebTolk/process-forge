# Journal replay development delivery, 2026-10-16

Status: private development archive installed; targeted qualification complete.
Public 1.2.0 remains unapproved. Executable source `44e 181213a 63f 4e 131be 8b 3d 7769d 736efd 40350`, clean tree
`9fdfe 9c 2517634b 993645b 775746b 42b 716ff 69a`. Exact archive SHA256 `fb 789c 703f 83220d 982be 92b 4fdf 6aa 7703da 93e 44bdf 2f 87c 1302b 3bf 5de 136`;
2447511 bytes, 1273 members, 1272 owned files.
1271 owned files match; one unchanged existing local configuration is preserved.
Ten backup preimages, three static configurations and 724pre-existing protected
project records passed verification. The native update was applied once without
force; previously owned Runtime restored on its first native start.

Accepted journal source and bounded service-state publication are included.
See [journal audit](../audits/journal-error-row-replay-20261016.md) and
[service audit](../audits/runtime-service-publication-20261016.md).
Rejected source revisions remain historical. CLI/MCP contracts and the partial
OOP migration boundary remain; no new public API or persisted journal index.

Clean schema/public/checksum, exact native archive quick, six original extracted
checks, installed doctors/focused checks, original full diagnostics and both
unchanged 180/240s public budgets passed. No allocator/assertion/timeout relaxation.
Five ordinary installedCLI Work-state reads: median 0.925230s; five independent
warm persistentstdio reads: 0.037910s. Different startup conditions; these are
reads, not useful Work creation or actual connected-host acceptance.

Actual restored Runtime remains degraded:45.00155s window, CPU42.781250s,
95.066percent of one core. Separate 20s GIL-only nonblocking
sampling collected 540stacks; supervisor/collection 293,
semantic_input 279. These inclusive counts overlap and cannot
be added or called CPU percentages. Current hot path repeatedly validates prepared
collection for still-active governed parent Work after capture. Existing code
already skips done/completed assignments; changing that same filter is insufficient.
Current scheduler/capture semantics and existing request-scope reuse need measured
investigation, not a status/mtime/TTL shortcut or unsafe empty projection cache.

Source operation batches improved, but this does not close the total Runtime CPU
blocker. OS evidence is read-only; no hardware/OS settings changed. Full 1.2source
and archive suites, version/changelog/migration and actual connected-host proof
remain ahead. Stop before stable publication for detailed report and explicit
approval. Broad smoke cleanup and device model policy remain separate tasks.
