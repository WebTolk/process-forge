# Project Conventions

Confirmed from `.pf/AGENTS.md`, the pinned process, existing modules, templates
and delivery evidence on 2026-09-27. These observations do not introduce a new
global platform/toolchain policy.

## Work and ownership

Read current context before work. Start/resume the governed Work, read its
assignment and immutable capsule, then use standard transitions with evidence.
ProcessForge chooses stages. Do not hand-edit lifecycle YAML, rewrite capsules,
silently skip optional stages or overwrite approved evidence. Keep unrelated
dirty work intact. The current pinned process permits one primary agent and no
subagents.

## Names, code and data

Use stable lowercase machine ids, consistent with existing process/artifact ids.
Python modules/functions follow existing snake_case names; preserve established
module boundaries and local style. Use UTF-8 text and explicit serialization.
Schema, YAML/JSON configuration and Python validation must agree. Domain-specific
rules belong in extension packages rather than hardcoded Core branches.

## Artifacts and review

Use [artifact-template](../../templates/artifact-template.md),
[review-template](../../templates/review-template.md) and
[handoff-template](../../templates/handoff-template.md). Record objective,
scope, inputs, changes, evidence, status and residual limits. Use append-only
logs. Distinguish current knowledge from historical proof. A `path_hint` is not
a mandatory filename. Do not mark a human approval when only self-review ran.
On Windows use `work-transition --evidence-file` for structured evidence.
Use UTF-8 file writes; the default PowerShell text-to-native pipe may be ASCII.

## Verification and delivery

Run checks relevant to the changed behavior. Existing Python checks live in
`tools/smoke_*.py` and `tools/validate-*.py`. Public changes require the project
schema/checksum/cleanliness gates; do not add unrelated test suites to a local
documentation-only task. Record actual commands and results.

Core delivery uses a qualified clean candidate, `release-pack`, consumer archive
validation, then `core-update plan/apply/status` when installation is authorized.
Preserve manifests and automatic backups. Source, archive, installed process and
connected host/MCP acceptance are distinct. Do not reinstall for private `.pf`
documentation changes. Runtime or host lifecycle actions require their own
applicable authorization.

## Documentation and privacy

Public behavior docs have English/Russian counterparts where the project uses
them. Keep public files free of secrets and machine-specific paths. Use local
documentation first. Record unavailable checks honestly. Temporary directories
belong under `.pf/tmp/`; protected historical evidence is never casual cleanup.

Sources: [project instructions](../AGENTS.md),
[pinned process source](../../packs/official/software-development/processes/software-feature-development.yaml),
[delivery](t07-engine-20260926/final/delivery.md).
