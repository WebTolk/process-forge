# Software Feature Development Process Authoring Example

This pack-local example accompanies the stable `software-feature-development`
process.

- Process: `packs/official/software-development/processes/software-feature-development.yaml`
- Prompt: `packs/official/software-development/prompts/software-feature-development-agent.md`
- Documentation: `packs/official/software-development/docs/processes/software-feature-development.md`

Use `lifecycle_mode: feature` for feature work with conditional delivery and
evolution, or `lifecycle_mode: full` when both are required. Explicit project/user
delivery requirements apply in either mode. Activate the pack in an authorized
workplace and validate the contract before using either mode:

```bash
python bin/pf.py pack-activate --id processforge.official.software-development --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
```

The scenarios below describe planning and acceptance decisions. Use the existing
Work and handoff contracts to record them. They introduce no new process fields,
stage routes, allocation stage, or worker permissions; the definition retains
`single_agent` execution and `simple_allowed` coordination.

## One Cohesive Extraction With Several Iterations

**Result:** move one existing service responsibility into its owning Core service
and migrate its affected consumers while preserving behavior. Acceptance covers the
service, consumer integration, existing formats and failures, and the agreed
delivery evidence. It does not cover an unrelated repository rewrite.

1. In orchestration and intake, record the result, affected scope, acceptance
   criteria, deferred work, lifecycle mode, and explicit delivery requirement.
2. Investigate existing code and tests, capture affected domain rules, then plan
   the responsibility boundary, dependencies, file ownership, rollback, focused
   checks, and final integration/regression assurance. Reuse current analysis.
3. During implementation, extract the service and run its affected checks.
   Integrate consumers and run the relevant compatibility checks. If a check
   exposes an incorrect assumption, refine the reasoning and approved plan as
   permitted, make the next edit, and rerun the affected checks.
4. Present the accumulated candidate for `code-assurance`. Reuse earlier evidence
   only while its provenance and applicability remain valid; rerun checks
   invalidated by later edits and assess integration across the whole result.
5. Apply the configured delivery profile and project/user publication policy at
   the agreed result boundary. Consolidate iteration observations in `evolve`.

The iterations stay within the current grants, tools, and PF-returned outcomes.
They do not create a backward transition or permission to overwrite an approved
artifact. A protected decision needs a reviewed revision; a scope expansion needs
a governed handoff/successor. There is no new Run, full suite, package, or
publication merely because one implementation step ended.

## A Substantial Native PF Worker Package Inside The Parent

For a contribution to the parent's current stage, first consider a native
executor consuming prepared input for the existing primary Assignment. This
requires a clear remit in authorized inputs and a writer handoff; it does not
require another Task or Run merely because the executor changes. Collection
preserves the governed parent stage, and the primary reviews the contribution
before supplying transition evidence. The orchestrator handles chat/Ledger
coordination unless those writes are explicitly granted to the worker.

Use a separately admitted child package when it has a worthwhile independent
scope and acceptance boundary, as in the following example.

**Parent result:** a cohesive behavior-preserving service change with current
documentation and acceptance evidence. **Child package:** the related EN/RU
documentation and worked examples, independently reviewed as one useful unit.

Use this arrangement only when the configured process, context, and explicit
assignment authorize delegation. Record the parent Run/Assignment and the child's
exact identity/context in the plan or handoff, along with frozen inputs, declared
outputs, dependencies, acceptance criteria, and non-overlapping write ownership.
The primary owns service/consumer changes; the child owns the specified companion
documents. Integration changes to a child's files require a clear writer handoff.

The child can legitimately follow a full process for its package: clarify its
scope, investigate supplied inputs, establish terminology, plan and produce the
documents, check them, and satisfy its own delivery/evolution obligations. This
is a nested contribution to parent acceptance. It does not make the parent
repeat its lifecycle or publish the parent result.

A native PF worker can execute an immutable prepared input without an MCP
connection. It uses only the delivered scope, actions, inputs, resources, and
output contract; it does not rebuild the capsule or start replacement Work.
Its report and collected outputs are implementation evidence for primary review.
Collection or a successful worker exit does not transition or complete the
governed parent. The primary integrates accepted output, checks the combined
candidate, and owns parent acceptance and delivery. Any child publication follows
its own explicit contract and grants.

## Related Small Edits As A Batch

**Result:** make the terminology for one public concept consistent across its
process documentation, companion translation, and examples.

When delegation is authorized, these related edits can form one worker package
with a common terminology decision, a bounded file set, and shared acceptance
criteria. Review terminology, links, and cross-document consistency together.
Individual wording changes are internal iterations; do not give every sentence a
separate worker lifecycle or publication.

If the task is one isolated wording correction, the primary can make and check it
directly when delegation would add no useful independent work. There is no worker
quota or minimum package size.

## A Small Independent Fix Is Still A Result

**Result:** correct one wrong link and confirm that readers reach the intended
document. That can justify a separate Run when it is an independently requested,
reviewable result; neither file count nor elapsed time imposes a minimum.

Use concise scope, reasoning, changed-file evidence, and a targeted link check.
Reference still-current facts instead of recreating unrelated analysis. Satisfy
the pinned process's required artifacts and gates. Record conditional delivery,
browser verification, or evolution as `not_applicable` only when the contract
permits it, with a reason and evidence. Explicit commit/publication requirements
still apply even to a one-line fix.

## An Iteration That Exceeds The Contract

**Situation:** an authorized local change reveals that fixing the issue also
requires changes to another service outside the assignment's write scope.

Record the finding, affected assumptions, and proposed follow-up. Stop the
dependent edits and use the governed handoff/successor mechanism for the expanded
scope. Preserve the existing capsule and approved inputs. Resuming reasoning
inside a result is not authority to widen grants, invent a backward route, or
bypass evidence requirements.

## Evidence And Delivery For The Combined Result

Keep focused iteration checks separate from final assurance in the plan. Carry
forward a result only while its identity, provenance, checked content,
dependencies, and relevant environment assumptions still match. Rerun the checks
invalidated by a later implementation or documentation edit. The final check set
follows the candidate's risk and integration needs; it is not an unrelated full
suite after every small change.

Declare whether acceptance requires source changes, an archive/package,
installation, publication, or connected-host verification. Report each boundary
actually checked. Build/package/install uses the configured delivery profile
inside assurance or `release-delivery`, not a new platform-specific process.
Follow explicit project and user policies; an internal iteration or child
completion cannot silently waive a requested delivery or authorize installation.

See the process documentation for lifecycle modes and the unchanged stage order,
and the [declarative execution contract](../../../../../../docs/concepts/declarative-process-execution.md)
for state, transition, evidence, and prepared-worker boundaries.
