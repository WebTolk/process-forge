# T01 — architecture, implementation plan and decisions

Status: design ready for implementation of documentation. Code follows in separate
T09/T02/T03/T04/T05 Works; this artifact does not advertise implemented commands.

## Boundaries and versioning

One application contract, multiple transports. Proposed responsibilities:
- `processforge_core/work_context.py`: neutral assignment intent normalization,
  immutable execution contract, pinned material descriptors, portable refs (T03).
- `processforge_core/work_resources.py`: explicit Work-scoped reads, intersected
  authorization, resource material/generation validation and result provenance (T02).
- `processforge_core/diagnostics.py`: neutral logger/config/records/sinks/export (T09).
- Trusted adapter registry near `tools/pf_runtime/`: validated built-in or
  operator-registered adapter objects; provider interpretation leaves common Host (T04).
- Existing worker preparation uses normalized contract and private prepared-input
  manifest before selecting a driver (T05). No wholesale CLI rewrite.

Keep outer capsule schema v1 readable. Add an explicit versioned `execution_contract`
block for new complete contracts; its version begins at 1. This avoids conflating
the old envelope version with new permission semantics. Missing block is legacy,
not an implied unlimited grant. Unknown contract version fails closed for execution.

The immutable block carries Work ids, stable assignment-intent digest, process pin,
snapshot id/checksum, selected material descriptors, scope/actions/outputs/capabilities
and explicit context rebuild policy. Hash intent fields only: lifecycle status,
stage evidence, timestamps, attempt/provider/model and diagnostic verbosity do not
alter the work contract. Raw historical assignment checksums remain legacy evidence.
The derived stage view carries current stage, allowed outcomes, obligations,
effective resource subset and verification status. Stage progression never edits
the immutable contract or rebinds Work to the newest project snapshot.

## Decisions

| ID | Decision | Implementation owner |
|---|---|---|
| D01 | Work = project/run/assignment; context id+checksum identifies immutable execution input; session/provider/attempt are separate | T02/T03 |
| D02 | Stage is a derived view of pinned process; stable intent digest excludes legitimate lifecycle mutation | T03 |
| D03 | Reads use pinned grants AND current authorization AND available pinned material; revocation wins over old cache | T02 |
| D04 | Missing stage subset inherits Work; explicit [] grants nothing; unknown/out-of-Work ids reject configuration | T02 |
| D05 | Read/write/deny/actions explicit; empty allowlist grants nothing; analysis-only forbids product writes | T03/T05 |
| D06 | Required sources, output paths and capabilities validated before launch; obligations do not add permissions | T03/T05 |
| D07 | Existing capsule never overwritten. Context change requires an explicit successor Work or separately versioned migration with reason and provenance; no silent in-place rebind | T02/T03 |
| D08 | Provider-specific provenance belongs to trusted adapters; common Host retains raw persistence, identity/project/attempt/path/hash checks | T04 |
| D09 | Prepared input is transport-independent and bounded; a driver launches one assigned Work, no nested bootstrap; retry has a distinct attempt identity | T05 |
| D10 | Eight severity levels, canonical strings and explicit Python numeric mapping; trace is a profile, not level; diagnostics separate from mandatory journal | T09 |
| D11 | Defaults < project < Work/session < invocation; fixed security/storage ceilings cannot loosen; effective values/source and timed detail override are visible | T09 |
| D12 | Redact before all sinks, bound recursion/size/storage, signal sink failures without masking operation; off only affects optional diagnostics | T09 |
| D13 | Correlation uses real request/Work/context/attempt; session null when absent; export is read-only, bounded and sanitized with manifest | T09 |
| D14 | Existing project search/resolve semantics stay explicit; Work search/resolve is additive, with generation provenance and coverage status | T02 |
| D15 | Public refs are portable; resolved local paths belong to private prepared runtime; PF grants do not claim OS sandbox enforcement | T03/T05 |

Metadata-only resource selection binds declared metadata. Fulltext/content sources
need a verifiable digest of the material they expose. A mutable output tree is not
silently frozen as a reference corpus. Missing/ambiguous legacy material identity
must be diagnosed and require explicit supported migration or successor Work;
never guess a current version from the same resource name.

Proposed additive read operations: Work-scoped application service exposed as
`work-search`/`work-resolve` and `pf.work.search`/`pf.work.resolve`, with explicit
run/assignment/context selectors. Names become callable only in T02. A supplied
context must match the selected Work, and a bound session must authorize its project.
Unscoped `pf.search`/`pf.resolve` remain project navigation.

## Documentation implementation

1. Write public docs/concepts/work-execution-contract.md with target/existing status,
   D01–D15 matrix: positive, negative, compatibility and diagnostic for each decision.
2. Add private .pf/adr/work-execution-contract-20260925.md using adr-template.md,
   reference accepted plan and source-backed investigation, state tradeoffs and
   current implementation boundaries. Include portable contract example in public doc.
3. Review consistency against source map and r01/r02 acceptance. Junior descriptive
   mapping allowed by new operator override; architecture owned by primary.
4. After implementation, request bounded junior document review with separate output;
   primary validates findings and fixes only this scope before assurance transition.
5. Validate new Markdown links, portability, diff scope and source lines. No product
   test suite is needed for a documentation-only change; semantic review is required.
6. Record delivery as docs-only, no package/deploy, capture evolution and close T01.
   Then start T09 automatically per AFK instruction.

Acceptance test matrix is part of the public contract. Diagnostics are target
stable names, not claims of current emitted errors. T09 sets and measures numeric
performance/storage budgets before code; this design requires boundedness but
does not invent measured performance. Installed Core remains at accepted T08 build.
