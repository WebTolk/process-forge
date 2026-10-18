# Historical private-dev readiness checkpoint, 2026-10-16

This page preserves the earlier private-dev checkpoint below, including its
failed diagnostics gate and unaccepted measurements. It is not the final
1.2.0 acceptance decision. The [release notes](releases/1.2.0.md) describe the
subsequent bounded stabilization; final qualification is tied to the exact
release source and archive before publication approval.

Version1.2.0, changelog and migration notes are prepared in this candidate.
Their final qualification and acceptance remain pending as part of the
release gates below.

**Release scope:**1.2.0 is an intermediate checkpoint of accepted refactoring.
Completing all five OOP epics, removing every legacy path or adding a new
Kernel/DI/plugin engine is outside this release boundary. Concrete quality
failures and compatibility checks remain separate release decisions. See the
[candidate notes](releases/1.2.0.md) and [migration notes](releases/1.2.0-migration.md).

**Not ready for public release.** Public tag, assets and update channel remain
unpublished pending the detailed report and explicit user approval.

Installed private dev source: `a480bc55589c76186bf4ab2fa8dc4a3f478031fa`. The [delivery report](releases/dev-collect-journal-20261016.md)
records its clean archive, one native update, preimages, preserved configuration,
unchanged protected history and one owned Runtime restore. Source, archive,
installed Core, independent stdio, actual Runtime and the actual connected host
have separate proof boundaries.

Journal multi-project snapshots and stable collect-refusal observation are
independently accepted. First/manual collect and new attempts preserve checks;
transient errors retry. Refusal remains failed and visible. F01-F03 identity and
fingerprint findings were corrected, with both failed reviews retained.

Clean schema/public/checksum, native archive quick, relevant original extracted
and installed checks, doctors and both unchanged public budgets pass. Native
task batch: 53.73s/180s; long-lived Runtime: 55.05s/240s.
The original diagnostics suite **fails** Windows parallel admission: five sink
failures. A retained probe reproduced a bounded 50ms wait timeout while a peer
held the critical section for79ms. No test or timeout was relaxed.

Installed ordinary Work-state reads: CLI median 0.938278s; independent persistent
stdio 0.082300s. Actual Runtime consumes 84.199% of one core after restore
and 90.207% in a separate settled window; health `degraded`. The previous
settled87.949% belongs to a different time/backlog. Overall speed is not accepted.
Repeated full collect nearly disappeared from sampled stacks; current costs
center on run enumeration/YAML and Runtime JSON state publication. Overlapping
stack counts are not CPU shares. Creation comparison: {"github-v1.1.0": {"samples": 10, "median_wall_seconds": 2.4047379000112414, "median_cpu_seconds": 2.28125}, "installed-current": {"samples": 10, "median_wall_seconds": 0.4243662999942899, "median_cpu_seconds": 0.3671875}}; small fixture, Core.start only, same pre-seal scope adapter;v1.1 has a smaller original authority model. Not large-project CLI admission.

Remaining release gates: overall performance and useful large-project admission,
the diagnostics failure, full accumulated source/archive suites,1.2.0 version,
changelog and migration notes, supported interpreter matrix, actual connected
host and explicit publication approval. CPython3.14.3 was executed; other
interpreters are not qualified by this slice. Work creation is owned by Core;
the default composition still includes legacy paths, so class counts do not
establish OOP completion. Full OOP epics remain separate from supported behavior.

Broad smoke audit/cleanup for the installed user Core and global device launcher
model policy are separate future tasks. See the source audits for
[journal snapshots](audits/journal-multiproject-index-20261016.md),
[collect recovery](audits/supervisor-collect-recovery-20261016.md),
[scope latency](audits/work-start-scope-latency-20261015.md), and earlier
[historical observation](releases/dev-historical-observation-20261016.md).
