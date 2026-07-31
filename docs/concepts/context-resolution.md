# Context Resolution

Context resolution converts workplace, project, process, package, template, tool,
and assignment inputs into a small set of files that a worker can use without
reading the entire repository.

Structured `parameters` are resolved as data, not as instructions. `AGENTS.md`
and other Markdown guidance are never parsed as machine parameter sources.

## Outputs

The resolver produces:

- Context Index: exact source list and fingerprints
- Resolved Rules: merged instructions grouped by policy type
- Conflict Report: blocked, warning, approval, and resolved conflicts
- optional Execution Context Package for an assignment
- optional Context Capsule for worker startup

## Source Order

ProcessForge keeps the existing cascade model:

1. core
2. workplace
3. organization
4. direction
5. specialization
6. platform
7. toolchain
8. project
9. process
10. stage
11. task
12. agent profile

Higher layers may narrow or extend behavior, but they cannot weaken locked hard
policies.

For parameter values, the first required machine layer is `workplace`.
Organization and direction layers are optional. A local station/global layer can
exist only when it is explicitly configured as structured data; plain global
agent instructions are not part of parameter resolution.

## Rule Classification

Rules are classified before merging:

- hard: never weaken or ignore
- locked: cannot be overridden by lower layers
- preference: may be replaced by a more local layer
- gate: controls entry, exit, or approval
- tool: selects or restricts tools and capabilities
- template: selects reusable artifact shapes

The resolver must not merge all instructions as plain Markdown. It records the
class and source of each rule so conflicts can be explained.

## Parameter Resolution

The parameter resolver merges active structured `parameters` blocks with the
same cascade order. It treats all namespaces uniformly: platforms,
toolchains, specializations, processes, projects, and tasks can contribute
parameters when their structured source is active, but the resolver does not
know domain semantics.

The snapshot records `resolved_parameters` plus `parameter_resolution` metadata:
sources, provenance, status, and conflicts.

For project snapshots, parameter resolution starts at the workplace layer. The
global agent instruction file is intentionally outside this machine merge. If a
team wants station-level parameters above the workplace, it must expose them as
an explicit structured parameter source; plain Markdown remains human/agent
guidance.

Current project snapshot sources include workplace `parameters`,
`registries/parameters.yaml`, active platform and specialization parameters,
project manifest `parameters`, local `overrides.parameters`,
`.pf/parameters.yaml`, and `.pf/parameters.local.yaml`. Assignment capsules add
assignment `parameters` on top of the pinned project snapshot.

The merge algorithm is intentionally close to a registry model: maps merge
recursively, scalars replace, lists of maps with `id` merge by id, lists without
ids replace, `null` removes a map key, and `_delete` or `__delete__` removes a
list item by id.

## Minimal Tool Behavior

`python bin/pf.py context-resolve --project-root <path>` writes the
context index, resolved rules, conflict report, and a private cache record. The
command is conservative: missing required sources or blocked conflicts prevent a
clean context status.
