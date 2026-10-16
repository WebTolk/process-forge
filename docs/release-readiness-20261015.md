# PF Public Release Checkpoint — 2026-10-15

The development checkpoint is **not ready for a new stable public release**.
Preserve the reviewed source checkpoint and continue bounded work toward 1.2.0. The unfinished
OOP programme alone is not a release blocker: supported behavior, contracts and
delivery evidence define readiness.

The [October 14 audit](audits/pf-audit-20261014.md) recorded 264 PASS / 3 FAIL
across 267 checks, four bounded contract defects and Runtime/timing observations.
Those results belong to its stated revision; they are not current full-suite
qualification for every subsequent change.

## Current Findings

- Runtime HTTP `read_body` now rejects invalid/negative/excessive lengths before
  reading, short bodies before decoding and non-finite JSON numbers, including
  float overflow. Focused inert-reader and isolated HTTP controls cover the
  source correction, valid byte framing, authorization and dispatch recovery.
  Run `python tools/smoke_runtime_http_body.py` alongside the cumulative candidate
  gates. Full candidate, installed Runtime and connected-host qualification
  remain separate; no network attack, socket stall or DoS is claimed.
- Native worker prepare/start now reject terminal governed Work before
  preparation/provider launch. Supervision keeps failed worker attempts separate
  from the governed assignment lifecycle, while active and supported legacy
  retries remain available. The existing prepared-execution recovery smoke
  covers the source correction and its side-effect boundaries. Atomic admission
  across different lifecycle locks is not established by this bounded fix;
  accumulated candidate, installed and connected proof remain separate.
- Current MCP changes enforce declared array bounds before business dispatch
  while preserving existing schemas. Focused counterexamples and controls cover
  the fix. They do not replace full accumulated release qualification.
- The legacy MCP optional diagnostic wrapper now checks canonical session-root
  identity as well as project ID. Eleven real-sink/dispatcher fixture controls
  retain exact responses and prevent the two observed foreign same-ID writes.
  See the [bounded report](audits/mcp-diagnostic-root-20261016.md). Installed and
  actual connected-host qualification remain separate.
- The bounded Windows diagnostics correction is installed; the full original
  smoke now passes with the shared Runtime stopped, under unchanged assertions
  and budgets. Earlier failures remain historical evidence. See the
  [current dev report](releases/dev-journal-lock-20261016.md).
- Source, clean candidate/archive, installed Core, Runtime and the application's
  actual connected MCP require separate proof. A connected process can disagree
  with current source context or retain older loaded tools after a disk update.
- Large-workspace admission latency and missing selected Python document bodies
  in prepared worker input were observed. Verified PF knowledge copies allowed
  the contribution within existing scope. Correct and measure these paths without
  claiming an unmeasured universal performance cause or bypassing permissions.
- The measured scope-overlap bottleneck now has a concrete Core owner shared by
  admission, supervisor and plan validation. Literal-prefix exclusion and one
  lazy normalized inventory preserve conflict decisions/reasons/order. Five
  current-project scope checks have a 1.782s median; full admission and installed
  profiling remain separate. See the [scope latency report](audits/work-start-scope-latency-20261015.md)
  for repeated comparable timings, controls and residual catalog/ambiguous-glob costs.

## Stable Release Conditions

The earlier development checkpoint installed cumulative corrections from source
`61a7b74cfa7b1812641d7cef85760449dccb06be`. Exact archive and native update,
installed original checks and measurements are recorded in the
[development delivery report](releases/dev-fast-work-20261016.md). Ordinary CLI
Work state has a 1.355501s median; fresh independent persistent stdio has a
0.0493904s median, with different process-start conditions. Native task batch
52.82s/180s and long-lived Runtime 54.54s/240s pass unchanged budgets. Source,
archive and installed targeted proof are complete for that development slice.

Stable blockers remain: restored shared Runtime consumes almost one CPU core and stays degraded,
full Work admission still takes about 19s, accumulated full suites/version/changelog
and actual connected-host proof remain outstanding. The new live profile centers
on HTTP event ingestion and stage-obligation rebuilding. No timeout/assertion was
weakened. Canonical selection and prepared YAML improvements do not close those
independent paths. Full OOP epics remain open. Public 1.2.0 still requires the
detailed ready-candidate report and separate user approval.


1. Qualify the framing and terminal-admission corrections in the accumulated
   candidate with retained positive, negative and retry controls; classify
   remaining supported-surface defects.
2. Reproduce or localize the prior Runtime registration and native task-batch
   budget failures. Increasing a timeout does not pass the published budget.
3. Prepare the 1.2.0 changelog, migration notes and the source
   commit. Preserve immutable existing release assets and tags.
4. Qualify one clean accumulated candidate: required schema/cleanliness/checksums,
   full source suite, archive/hash/provenance and full extracted tests, then
   applicable clean-install/update and fresh connected-host checks.
5. Satisfy the [publishing contract](maintainers/release-publishing.md), verifying
   exact tag, commit, assets and update-channel readback.

Use focused development checks while confirmed stable-release blockers remain.
Reserve the full public/archive cycle for a candidate capable of passing the
release conditions. Class counts, completed tasks and the historical fraction
of passing tests do not provide a meaningful readiness percentage.

## Source preparation before the device update, 2026-10-16

Bounded diagnostics admission and current-byte journal source are independently accepted. See the [next private development delivery](releases/dev-journal-lock-20261016.md) and its separate archive/install/profile status. Rejected journal variants are excluded; final real-history batch median9.515165 to7.753035s uses conservative full parsing because of one malformed row. These source results do not replace the installed61 baseline or qualify Runtime CPU, the actual connected host or stable1.2.0.

## Installed journal/diagnostics dev checkpoint

The [new private development delivery](releases/dev-journal-lock-20261016.md) records exact new executable/archive/update and current Runtime evidence. Its installed original diagnostics check now passes; the earlier failure is historical and retained. Full stable qualification and explicit publication approval remain outstanding.

## Ordered journal replay candidate, 2026-10-16

Accepted ordered error-row replay and bounded service-state publication are included in the [next private development delivery](releases/dev-journal-replay-20261016.md). Source batch results preserve bytes/errors but do not qualify actual installed Runtime CPU. A new clean archive, one manifest-owned update and quiet profile are required; full public release and connected-host gates remain open.
