# Project Profile

## Status and purpose

Reviewed from project source and delivery evidence on 2026-09-27. ProcessForge
is a file-first framework for defining, versioning and executing governed work.
Assignments, immutable execution contexts, artifacts, gates and handoffs make
work reproducible across executor providers. Runtime, MCP and provider adapters
extend the file model; they are not prerequisites for Garage/file-only work.

## Identity and implementation

- Project id: `process-forge`; manifest type: `processforge-development`.
- Current classifier type: `software.python`; this describes the implementation,
  not a mandatory platform overlay.
- Product version: `1.1.0`. Exact accepted installed build: `ddff5983`.
- Implementation: Python; process/package/config data: YAML and JSON; schemas:
  JSON Schema; documentation: Markdown. Runtime dependency: `PyYAML>=6.0`.
- Python 3.11+ is recommended by the project README. No platform or toolchain
  overlay is selected in the current project context.
- Default project process: `software-feature-development@1.1.0`.

## Layers and present behavior

Core owns context/pinning, lifecycle, authorization, evidence and durable events.
Official processes/packages are extension data under `packs/official/`.
Workplace configuration is separate from project state. Provider adapters and
MCP are integration boundaries. See [repository map](repository-map.md).

The T01-T10 delivery includes Work contracts, authorized resource access,
normalized context, provider adapters, prepared immutable input, integrated
acceptance, optional diagnostics, a local monitor and the T07 egress engine.
The qualified strict-egress route is managed HTTP/JSON on Windows. Native Codex,
generic-shell and isolated-local strict egress remain unsupported. A prior
installed-process test is not proof that a connected application MCP reloaded.

## Ownership, privacy and work entry

Use `.pf/AGENTS.md`, current context and the selected assignment/capsule. One
writer owns each file scope. Approved artifacts and recorded capsules are
protected. Public distribution files must not contain machine paths or secrets;
`.pf` evidence, Runtime state, private local configuration, archives and backups
have separate delivery/privacy boundaries. Retain declared durable evidence.

Start with the [artifact index](README.md), [conventions](project-conventions.md)
and [verified delivery](t07-engine-20260926/final/closeout.md).

## Evidence

[Product README](../../README.md), [dependencies](../../requirements.txt),
[project manifest](../process-forge.yaml),
[delivery report](t07-engine-20260926/final/delivery.md),
[current coverage](artifact-completion-20260927/coverage.md).
