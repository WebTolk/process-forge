# Context Cache

The context cache is an accelerator, not the source of truth. Source of truth
remains the manifests, process definitions, packages, templates, assignments,
artifacts, reviews, logs, handoffs, and ADRs.

## Location

Runtime cache files live under:

```text
.pf/runtime/cache/
```

This path is private runtime state and must be ignored by version control.
Legacy root-layout projects may use `runtime/cache/` until migration is
reviewed.

## Cache Records

A cache record stores:

- generated timestamp
- project flow fingerprint
- source fingerprints
- context index fingerprint
- resolved rules fingerprint
- conflict report fingerprint
- health status

The cache may be reused only when all required source fingerprints still match.

## Stale Rules

Context becomes stale when any required source changes, disappears, or gains a
different checksum. An Execution Context Package becomes stale when its
assignment, process definition, package manifest, template, or recorded context
index changes.

## Ownership

A single-agent session may rebuild stale context when the Session Start Request
allows it.

An orchestrator should rebuild context once, then pass Execution Context
Packages or capsules to workers.

A worker should not rebuild whole-project context unless its capsule explicitly
allows it.
