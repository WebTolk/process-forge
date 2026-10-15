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
- Native worker prepare/start still needs the terminal governed Work versus
  failed worker-attempt policy identified as PF-AUDIT-04. The new MCP facade
  rejects terminal Work before native invocation; this does not repair the older
  CLI path or establish atomic cross-lifecycle admission.
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

## Stable Release Conditions

1. Qualify the framing correction in the accumulated candidate and resolve
   terminal-admission defects with retained positive, negative and retry
   controls; classify remaining supported-surface defects.
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
