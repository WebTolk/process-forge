# Parameter merge: admitted implementation

Date: 2026-10-18. Baseline: dev d2f8a856565e77b5f1a6d3026369e861800ccffb.
The user authorized sequential implementation, mode 1-1-4 with native shell workers,
independent clean-context review, focused checks and commit/push to both dev remotes.
Work autonomously until 2026-10-19 09:00 device time (UTC+04), then finish current tasks.
MCP resources and other new functionality remain separate future work.

## Domain and architecture

Accepted predecessor: ../pf121-architecture-cycle-20261018/implementation-plan.md
and domain-model.md. Original documents remain authoritative: migration-contract.md
in original-architecture-alignment-20261010, progressive-oop-boundary-20261010/decision.md,
oop-refactor-clarification-20261005/clarification.md, pf-framework-architecture-20261005
adr.md, domain.md and direction.md, python-framework-20261005/oop-03.md.
The primary reread these documents and src/processforge_core/AGENTS.md before admission.

The coherent responsibility is existing parameter merge with ordered provenance.
Its owner is ParameterMergePolicy in processforge_core.configuration.parameters.
It is a stateless policy object with public instance method:

    merge_maps(base, override, source_id, path="", provenance=None)

Move the five existing helper algorithms into this owner; other helpers may become
private instance methods. No callbacks, imports, providers, aliases or facades pointing
back to tools/processforge.py. No new package dependency, framework or validation.
Use direct owning-module imports at every consumer. Remove all five old definitions.
add_parameter_source and work.context.build_context_fields keep their other behavior;
the full context compiler is still partly dependent on the legacy monolith.

Exact preservation includes dict iteration order, str(key)/str(id), native exceptions
and their order, None deletion, truth-is-True deletion markers, initial empty-list
replacement, deep copies, mutation of an explicitly supplied provenance object,
duplicate IDs, provenance order and the existing quirk that appending an ID item
does not update the ID index. Do not fix that behavior during extraction.

## Ownership and execution

One writer per file. The primary writes only its artifacts, handoff and scratch.
Four native workers have disjoint ownership: core owns the new parameters.py;
consumers owns tools/processforge.py and work/context.py; docs owns EN/RU Core map
and checksums/processforge.sha256; QA writes only its artifacts and scratch.
Core and consumers may implement concurrently against the exact API above.
Docs and QA begin after implementation. The independent reviewer starts after
implementation and QA, reads the actual diff with a clean context and writes only
its own evidence. No worker commits, pushes, changes infrastructure, starts nested
agents or independently moves lifecycle state. The primary performs native transitions
only after actual stage requirements are satisfied.

All worker starts use exact fresh PF identities and immutable capsule checksums.
Source project-context-check is fresh/ready on ctx-20261018-083156-60cda1. Connected
MCP has known installed/source drift; use existing source CLI without refreshing
context or restarting/installing Runtime/MCP/Ledger. Never use an unrelated active Work.
Use Serena first for symbols where available; bounded source-only rg/AST otherwise.
Preserve all unrelated dirty state. Scratch stays in each worker's .pf/tmp subtree.

## Focused assurance and delivery

Capture baseline helper code before modification as baseline-functions.json, with
source hashes. QA compares rich bounded cases against it, including values, errors,
ordered provenance, copies, malformed inputs, duplicate and deleted IDs. Verify
normal owner use from copied Core without CLI/Host. Run existing parameter cascade,
assignment capsule and freshness smoke scripts; no full release suite or new permanent
test suite for the move. Set TMP/TEMP/TMPDIR into short owned scratch for smoke fixtures.
Record code review findings and resolve blocking ones before delivery.

Update the current ownership map and only changed shipped checksum entries, preserving
unrelated .pf configuration drift. Preserve released CLI/MCP names, arguments, errors,
response payloads, protocol formats and ordering. Qualify this as source-only evidence;
archive/installed/Runtime/connected-host acceptance are separate and untested here.

After independent review, complete native lifecycle and commit the exact owned result.
Push the same SHA to origin/dev and gitverse/dev and read back both. GitVerse uses
existing GITVERSE_TOKEN through process-only HTTP authorization with credential helper
disabled. Never write or print credentials. Reread original architecture after completion
before admitting the next bounded responsibility.

## Python knowledge used

The primary resolved docs.python:root, docs.python-practices:root and docs.python-peps:root
with exact Work selectors; provenance receipts are retained in its private scratch.
Read local official mirrors data-model.md (identity, mutable containers and references),
stdtypes.md (ordered mutable collections), practices/pep20.md (explicit simple ownership),
descriptor.md (ordinary bound methods) and typing-guide.md. Use one ordinary class,
existing deepcopy semantics and explicit imports; do not introduce container/DI machinery.
Workers may resolve the same PF resources for additional focused reading as necessary.
