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
- Older MCP operations retain optional diagnostic routing based on project ID.
  A current isolated `pf.resolve` control creates diagnostics in a different
  same-ID directory before business validation. New action tools avoid that
  wrapper until their own admission checks; legacy routing still needs repair.
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

The scope repair has since been installed from its exact development archive.
Owned bytes, backups and protected history matched; ordinary independent installed
stdio/context checks passed. Two isolated native checks now pass their unchanged
budgets: task batch 57.00s/180s and long-lived Runtime 67.84s/240s. The real shared
Runtime remains degraded and consumed almost one CPU core in a bounded OS sample.
These targeted results do not replace the accumulated public suite or actual
connected-host qualification.

The [bounded prepared YAML report](audits/prepared-resource-yaml-latency-20261015.md)
records another source correction, exact guard controls and a modest five-pair
native collect improvement. Installed/live Runtime acceptance of that newer
source remains separate. A detailed readiness report and separate operator
approval are required before public 1.2.0 tags, assets or stable-channel updates.

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
