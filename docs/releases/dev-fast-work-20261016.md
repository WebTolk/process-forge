# Development delivery and measured Work latency, 2026-10-16

This private development iteration is installed and qualified for the targeted
checks below. Public 1.2.0 is not ready or approved. The executable source is
`61a7b74cfa7b1812641d7cef85760449dccb06be`, clean tree
`deb115ab9bfa981cb4cec598719eaeca461a6efa`. The 1.1.0 development archive has
SHA256 `309528f60429bb1dd31450808ee268950a2c21c7fb22fce6f88eba2f37990f80`,
2,395,125 bytes, 1,257 ZIP members and 1,256 owned files. A later documentation
commit records these results; it does not change the installed executable identity.

The cumulative payload includes the common scope-conflict repair, bounded prepared
YAML reader, MCP diagnostic canonical-root binding and user-approved canonical
Run+Assignment selection. See the [canonical audit](../audits/canonical-work-selection-20261016.md).
The verified pair retains four current reads including final identity proof;
unproved or incomplete queries retain the existing catalog fallback.

The native manifest update applied once without force. Verification matched 1,255
owned files and preserved the single pre-existing unchanged local configuration
exception. All 12 changed-file preimages, three static configurations and 704
protected project records matched their captured hashes; no incomplete update
remained. The owned Runtime was stopped and restored through native ownership
guards. Other host processes were not part of this qualification.

| Installed observation | Result | Conditions |
| --- | --- | --- |
| Ordinary CLI exact Work state | Median 1.355501s, five samples | Full launcher/process cost; unchanged selected Work |
| Fresh independent ordinary MCP stdio exact Work state | Median 0.0493904s, five requests | Warm persistent process;49ms is not a CLI startup figure |
| CLI context freshness check | Median 3.002398s, five samples | Separate context path |
| Independent stdio `pf.context` |10.806944s, one request | First context request; not the actual connected host |
| Native task batch |52.82s /180s, PASS | Original script and budget |
| Native long-lived Runtime |54.54s /240s, PASS | Isolated test Runtime, original script and budget |
| Original general diagnostics smoke | FAIL,17.356468s | Same multiprocess sink assertion; unchanged budget |

The installed measurements above ran with the shared Runtime stopped and no
model workers or profiler active. Seven related original installed scripts and
project/workplace doctors passed. The exact archive passed native quick
qualification and five related extracted checks. These focused development
checks do not replace the full accumulated source/archive suites.

Five earlier alternating actual-project direct CLI pairs retained identical
full outputs and selected documents: old installed scope-only Core median 6.351549s,
reviewed cumulative source 1.349780s. This comparison included process startup
and the old shared Runtime was active. The later quiet installed median is a
separate observation, not an additional controlled before/after ratio.

After restoring the new shared Runtime, a 45.000778s read-only OS sample recorded
44.953125 CPU seconds,99.894% of one core, and health remained degraded. The new
20s attached GIL profile collected 712 successful stack samples;561 included HTTP
event ingestion and 148 included stage-obligation rebuilding. Counts overlap and
are not percentages of CPU time. Every accepted derived event currently rebuilds
project projections. Separate scoped investigation must establish a safe correction;
the Work-state improvement does not close the background CPU defect.

The general diagnostics failure also reproduced while the shared Runtime was
stopped. Existing observations locate Windows byte-lock acquisition failures
within its 50ms budget. Preserve the test and budget while repairing the cause.
Full Work creation remains a separate latency path: a genuine later unprofiled
repair admission took 18.910s; a separate profiled admission is retained for
localization. Core extraction remains partial and the OOP epics remain open.

Before public 1.2.0: repair these measured defects, prepare version/changelog and
migration notes, qualify a clean accumulated candidate with full required suites,
applicable install/update and actual connected-host proof, then present a detailed
readiness report and obtain separate user approval. Do not publish stable tags,
assets or channel metadata beforehand. Broad smoke cleanup and the device model
allow-list are separate future tasks.
