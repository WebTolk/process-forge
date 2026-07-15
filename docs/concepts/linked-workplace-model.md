# Linked Workplace Model

ProcessForge uses linked mode as the primary operating model.

In linked mode the ProcessForge distribution and shared workplace resources live
outside individual projects. A project receives a thin `.pf/` flow directory
with project settings, assignments, artifacts, logs, reviews, handoffs,
contexts, events, telemetry, and runtime outbox files.

Projects do not copy the ProcessForge core, global schemas, global tools,
global templates, platform contracts, or large knowledge trees into `.pf/`.
They connect to those resources through the workplace manifest and registries.

The required project-local files are:

- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml` unless the project explicitly uses no-local bootstrap mode
- `.pf/hooks.yaml`
- project artifacts under `.pf/`

The required workplace files are:

- `workplace.yaml`
- `terms.yaml`
- `registries/distributions.yaml`
- resource registries for packages, platforms, templates, tools, MCP, and knowledge roots

Embedded copies of the ProcessForge core are future/optional and are not the
default path.
