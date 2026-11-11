# Tasks, local PF and GitHub

[Русская версия](../ru/contributors/task-collaboration.md)

Use PF to conduct substantive development of ProcessForge. Keep its project state
local and ignored by Git. Shared instructions, knowledge profiles, process
definitions and accepted design decisions are versioned; another contributor
creates their own context and Work. A public issue is not a backup of local PF.

## Select the task source

The [shared profile](collaboration-profile.json) sets `local_pf` for current 1.3.0
development. Record the selected mode in the local project's supplemental fields.
An explicit maintainer decision can select `github` for repository-led work.
An issue's existence or temporary network failure never changes the mode.

| Rule | `local_pf`: GitHub is a mirror | `github`: GitHub is the task source |
| --- | --- | --- |
| Task begins | Local PF accounting or an accepted maintainer request. | An existing or newly created GitHub issue. |
| Before Work | Define the local objective, scope and acceptance criteria. An issue is optional. | Read the issue and discussion; bind the Work to its URL before execution. |
| Work and iterations | One substantial task may require several Work and iterations. | Several local Work and contributors may address one issue. |
| Changes to scope | Accept in local PF, then publish a useful summary. | Agree in the issue, then reconcile the local Work/context through PF. |
| Public updates | Publish major tasks, accepted decisions, blockers, deliverables and verification results. | Keep the shared issue informed of accepted progress and blockers. |
| Remote feedback | Review proposals and incorporate accepted changes into local accounting. | Read the current shared decisions before continuing local execution. |

An issue describes one bounded problem or outcome and its acceptance criteria.
A version such as 1.3.0 can include many such issues; use a GitHub milestone when
publishing the version's shared progress. A Work is an execution unit, not a
one-to-one issue copy. Avoid creating issues for every stage or retry.

In `local_pf`, absence of GitHub access does not prevent permitted local work;
record publication as pending. In `github`, a missing issue or unavailable current
task decision blocks dependent execution; report the missing input. Neither mode
changes the branch/check/PR/review delivery route in CONTRIBUTING.

## Supplemental link fields

These are a contributor convention in the existing extensible project and
assignment documents, not new CLI arguments or a built-in synchronization API.
They are ordinary metadata, separate from execution `parameters`, stage/status,
permissions and immutable capsules. Use supported local metadata/authoring
operations; never edit lifecycle state or a pinned capsule to add a URL.

For the project, merge this fragment into `.pf/process-forge.yaml`, preserving
its existing identity and other fields. Start with the shared profile's values:

```yaml
project:
  id: process-forge
  name: ProcessForge
  collaboration:
    task_source: local_pf
    repository_url: https://github.com/WebTolk/process-forge
    integration_branch_url: https://github.com/WebTolk/process-forge/tree/dev
    target_version: 1.3.0
```

For a selected Work, place supplemental links at the top level of its local
assignment document. The following URLs are placeholders; use actual issue,
branch and PR URLs and omit links that do not exist yet:

```yaml
collaboration:
  issue_url: https://github.com/WebTolk/process-forge/issues/NUMBER
  branch_url: https://github.com/WebTolk/process-forge/tree/WORKING-BRANCH
  pr_url: https://github.com/WebTolk/process-forge/pull/NUMBER
```

`integration_branch_url` identifies the delivery target. `branch_url` identifies
this Work's working branch. Never use one as an implicit substitute for the other.
Several assignment documents may carry the same `issue_url`. A Work's lifecycle
and its exact PF selectors remain independent of the issue number.

The agent must read these fields from the actual manifest and selected assignment
as part of context acquisition. A compact `pf.context`/`pf.work.state` response
may omit supplemental metadata; schema acceptance alone does not prove delivery.
Use the authorized project/Work read path and record the effective mode and links
in the working handoff. Do not assume unknown tool arguments will be persisted.

If links exist in an older parameter layout, read and reconcile them before
writing a second copy. Changing pinned parameters, objectives, scope or branch
permissions requires the normal PF context/successor route. Updating a public
link does not itself authorize an execution-context change.

## Agent behavior

1. Read the shared profile, local collaboration fields, valid PF context and exact
   selected Work. If local and shared mode differ without a recorded maintainer
   decision, resolve that discrepancy before publishing or changing task scope.
2. If `issue_url` exists, read the issue and current discussion. Apply the selected
   mode's authority; a mirrored issue cannot silently replace the local objective.
   In `github` mode, obtain the issue URL before starting the bound Work.
3. Inspect Git state. Check that `branch_url`, repository and actual checkout match.
   Preserve unrelated work; use an isolated branch/checkout for the selected scope.
   A discrepancy requires reconciliation, not a forced checkout or reset.
4. Execute the PF stages, record evidence and retain exact Work identity. Read only
   relevant knowledge. Bootstrap and diagnostic reading may happen before a Work;
   missing PF readiness blocks substantive execution, not the ability to repair
   the explicitly authorized setup.
5. At a publication or delivery stage, publish the authorized public summary to the
   linked issue/PR. Include decisions, results, tested revision/platforms and what
   remains. Preserve other participants' text and discussion. Keep local paths,
   capsules, credentials, raw journals and unreviewed draft reasoning private.
6. In `local_pf`, create a mirror issue when publication is authorized and useful;
   save the returned URL and update that issue on later iterations. Check the local
   link and repository for an existing issue/PR before creating another. In
   `github`, update the existing shared task rather than creating a parallel copy.
7. Save the actual working branch and PR URLs in supplemental metadata when they
   become available. A stored URL describes a relationship; publishing, push,
   merge and close actions follow the authorized process and repository policy.

## Completion and continuation

Completion/cancellation of one Work does not close or reopen an issue. Intermediate
PRs reference the issue without closing keywords. Close the issue only when the
whole outcome meets its criteria and accepted changes are integrated into `dev`,
unless the issue explicitly requires release acceptance. Use `Closes #NUMBER`
only for that final PR. GitHub applies closing keywords on the default branch;
check its actual setting rather than assuming that it is always `dev`.
See [GitHub's linking rules](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).

Another device/contributor reads the issue, accepted code, public design decisions
and checks, then creates its own local PF Work. Exact continuation of someone's
private Work requires an explicit state transfer and valid PF continuation;
it cannot be reconstructed from an issue summary alone. Do not import another
developer's capsules or device paths as a project setup dependency.

Changing the task-source mode is a recorded maintainer decision: reconcile open
tasks and their links, define the effective scope, then follow PF's rules for
affected active contexts. Do not rewrite completed Work history. No automatic
two-way synchronizer is assumed by this convention.
