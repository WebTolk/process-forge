# Software Feature Development

> Production process from the official bundled
> `processforge.official.software-development` pack.

## Purpose

`software-feature-development` is a neutral software lifecycle process. It
guides one cohesive software result from orchestration and intake through
investigation, domain understanding, architecture, iterative implementation,
integrated assurance, release delivery, and evolution capture.

The process keeps its existing stages, gates, artifact requirements, allowed
tools, execution mode, and coordination policy. The guidance below explains how
to apply them; it does not add routing or delegation mechanisms.

## Choosing The Result Boundary

A Run covers one cohesive result that can be reviewed and accepted against
explicit criteria. Record its objective, acceptance boundary, included and
deferred work, and delivery requirement during orchestration and intake. For a
nested package, also record the parent Run/Assignment in the plan or handoff.

Dependencies, integration needs, and acceptance criteria determine this boundary.
Several related changes may belong to one result. A small independent bug fix
can also be a complete result; there is no minimum duration, file count, or
change size. A function, tool call, worker response, local test, or commit does
not automatically define another Run.

Tasks and iterations organize work within that boundary. They do not require a
fresh lifecycle, final assurance, package, installation, or publication after
each contribution. See [Process Definition, Run, Task, Iteration](../../../../../docs/concepts/process-definition-run-task-iteration.md).

## Lifecycle Modes

| Mode | Application |
| --- | --- |
| `full` | Full lifecycle; release delivery and evolution are required. |
| `feature` | Normal feature development with conditional release delivery and evolution. |
| `bug_fix` | Focused investigation, impact analysis, implementation, regression assurance, and conditional delivery, release notes, and evolution. |
| `debug_loop` | Repeated investigation, implementation, and checks; delivery is not required by the mode, and evolution is conditional. |
| `implementation_only` | Requires existing or explicitly supplied `scope`, `investigation-report`, and `implementation-plan` inputs; delivery is not required by the mode, and evolution is conditional. |

Select the applicable mode during orchestration and respect the current Work
contract. A mode label does not create backward transitions, waive required
inputs or gates, or authorize another action. Explicit project and user delivery
requirements still apply.

When the contract permits a conditional operation to be omitted, record
`not_applicable` with a concrete reason and evidence. Optional stages and
artifacts must not be silently skipped; task size alone does not waive a
requested delivery.

## Stages

| Stage | Application to the agreed result |
| --- | --- |
| `orchestration` | Establish the cohesive result and acceptance boundary, lifecycle mode, context snapshot, exact Work identity, coordination mode, parent reference when nested, and delivery profile availability. |
| `intake-scope` | Capture included and deferred work, non-goals, acceptance criteria, risks, unknowns, and delivery and publication requirements. |
| `investigation` | Inspect affected code, configuration, tests, documentation, compatibility, migration risks, and evidence paths; reuse current validated facts and investigate gaps. |
| `domain-modeling` | Capture or reference domain terms, rules, and platform constraints; record relevant refinements without recreating unchanged analysis. |
| `architecture-plan` | Define the cohesive approach, dependencies, file/module ownership, implementation plan, decisions, rollback concerns, focused checks, and integrated assurance plan. |
| `implementation` | Build the integrated candidate through scoped reasoning, approved revisions, edits, and targeted checks; record changed files and the change summary. |
| `code-assurance` | Assess the accumulated candidate against acceptance criteria and the verification plan, including relevant integration, regression, and conditional browser/UI checks. |
| `release-delivery` | Apply the agreed delivery requirement and explicit policies through the configured profile; record delivery evidence or a permitted, justified `not_applicable` decision. |
| `evolve` | Consolidate observations from internal and worker iterations into evidence-backed lessons and proposals, or record a permitted `not_applicable` decision. |

## Internal Iterations

One result can require repeated investigation, domain and architecture reasoning,
plan refinements, implementation, and focused checks. For example, a targeted
test may reveal an assumption that needs another design decision and edit before
the integrated candidate is ready for assurance. Completing such an iteration
does not itself restart the process or trigger delivery.

Keep these activities within the current stage's explicit actions, scope,
resources, and allowed tools. Use only outcomes returned by PF. Reasoning about
an earlier decision does not move lifecycle state backward or grant permission
to edit its approved artifact. Preserve approved artifacts, process pins, and
immutable capsules; use a reviewed revision or governed handoff/successor when
the required change exceeds the current contract.

Keep artifacts proportional to the decisions. Reference still-valid facts and
evidence instead of recreating the full artifact set for each iteration. Record
changed assumptions and decisions where they affect acceptance or verification.

An input referenced by accepted evidence or a pinned hash must retain its bytes,
even if its editorial status is not approved. A revision is a separate file
connected through the declared input/evidence or governed handoff mechanism;
overwriting the consumed input invalidates its evidence.

After a transition, use the complete current Work state returned by PF. Read
state again when that projection is missing or after uncertainty, reconnect, or
concurrent changes. A successful transition with a complete current projection
does not require a second identical read. See [Declarative Process Execution](../../../../../docs/concepts/declarative-process-execution.md).

## Nested Worker Assignments

For a permitted contribution to the current stage, a native executor can consume
prepared input for the existing primary Assignment. Hand over product writes
while it runs, then review the collected output. Changing the executor alone
does not require another Task or Run. A separate independently scoped package
uses its own admission when that boundary is warranted.

Provide the worker's remit and coordination requirements in authorized inputs.
Do not ask it to write chat, Ledger, or other state outside its grants; the
orchestrator performs coordination that remains outside the worker's scope.

The definition retains `single_agent` execution and `simple_allowed`
coordination. Delegation requires permission from the configured process,
current context, and explicit assignment. These descriptions and an available
worker capability do not supply that permission or introduce an allocation
stage.

Where delegation is authorized, give a worker a substantial independent package
or a useful batch of related small tasks. Define its inputs, outputs, exact
identity/context, dependencies, acceptance criteria, and non-overlapping write
ownership. Keep an isolated tiny edit with the primary when a separate worker
lifecycle would add only coordination. Neither choice imposes a minimum size on
a legitimate standalone result.

A substantial child package may follow a complete process of its own while
remaining nested within the parent's delivery boundary. Record that relationship
in the plan/handoff; do not infer a new runtime relationship or API. A native PF
worker executes its own authorized assignment or prepared input without widening
its grants or rebuilding its immutable context. Collection supplies the output
and evidence for primary review; worker exit or child completion does not
complete, restart, or publish the parent Run.

The primary integrates accepted contributions, resolves dependencies, and
assesses the combined candidate before parent acceptance and delivery. A child's
own delivery obligations follow its contract and do not authorize parent
publication.

## Checks And Evidence

Plan focused checks for each affected area and risk-based final assurance for
the integrated result. Run checks relevant to an iteration, then assess the
accumulated candidate at `code-assurance`. Include integration and regression
checks when the changes and dependencies require them. An iteration ending does
not by itself require an unrelated full suite or another package/install cycle.

Reuse earlier evidence only while its identity, provenance, checked content,
dependencies, and relevant environment assumptions still apply to the candidate.
Later edits require rerunning the checks they invalidate. A worker report or a
passing local test contributes evidence; it does not establish parent acceptance
on its own. Record actual results, remaining limitations, and justified
`not_applicable` decisions against the current obligations.

## Delivery Boundary

Apply release and delivery to the agreed result according to explicit project
and user policies for commits, publication, packaging, release, and installation.
Record those requirements in intake and the plan. Do not silently replace a
requested publication or installation with a source-only result. An internal
iteration or child completion does not authorize those operations.

Delivery/build/package/install is an operation profile, not a separate
ProcessForge process. Platform-specific delivery belongs in project or platform
profiles:

```yaml
process_id: software-feature-development
execution_profile:
  delivery_profile: project.default_delivery
```

Do not add platform-specific public core processes such as
`joomla-plugin-delivery`. A Joomla, WordPress, Laravel, or other platform
project can define its own delivery profile through platform contracts or
project-local configuration. Report source, package/archive, installed, and
connected-host verification according to the boundaries actually checked.

## Evolution

The lifecycle `evolve` stage uses the same top-level common `evolve` contract as
non-software processes. It writes local candidates and an `evolution-report`; it
does not auto-train models or mutate global packages.

Collect observations during iterations and consolidate them at the agreed result
boundary. A proposal is not an approved rule or permission to change a shared
package.

Its evolve targeting allows `knowledge_package`, `delivery_profile`,
`process_definition`, `project_rule`, and `platform_contract`. Build and release
commands are delivery-profile candidates, process-flow findings are
process-definition candidates, project-only constraints remain project rules,
and platform constraints require explicit applicability. Child-platform findings
are not promoted to parent-platform rules without reviewed evidence.

## Legacy Mapping

| Legacy concept | ProcessForge concept |
| --- | --- |
| orchestration | `orchestration` |
| intake | `intake-scope` |
| investigation | `investigation` |
| domain | `domain-modeling` |
| architecture | `architecture-plan` |
| implementation | `implementation` |
| assurance | `code-assurance` |
| release | `release-delivery` |
| evolve | `evolve` |
| instruction update | `instruction-update-proposal` |
| delivery/build runner | delivery/build profile, not process |

## CLI Checks

```bash
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
python bin/pf.py builtin-process-catalog-doctor --root . --public
```
