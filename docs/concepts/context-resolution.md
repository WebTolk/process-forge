# Context Resolution

Context resolution converts workplace, project, process, package, template, tool,
and assignment inputs into a small set of files that a worker can use without
reading the entire repository.

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

## Minimal Tool Behavior

`python tools/processforge.py context-resolve --project-root <path>` writes the
context index, resolved rules, conflict report, and a private cache record. The
command is conservative: missing required sources or blocked conflicts prevent a
clean context status.
