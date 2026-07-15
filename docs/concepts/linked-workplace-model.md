# Linked Workplace Model

ProcessForge uses linked mode as the primary operating model.

In linked mode the ProcessForge distribution and shared workplace resources live
outside individual projects. A project receives a thin `.pf/` flow directory
with project settings, assignments, artifacts, logs, reviews, handoffs,
contexts, events, telemetry, and runtime outbox files.

Projects do not copy the ProcessForge core, global schemas, global tools,
global templates, platform contracts, or large knowledge trees into `.pf/`.
They connect to those resources through the workplace manifest and registries.
Package manifests and package indexes are resolved through
`registries/package-roots.yaml`; linked projects record selected package ids,
required/recommended status, and resource index records, not resolved package
root paths.

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
# Path Constants In Linked Mode

Linked projects do not copy global knowledge, templates, tools, MCP, or platform contracts. They reference workplace registries.

`workplace.yaml:path_constants` defines base paths such as `PF_KNOWLEDGE`, `PF_TEMPLATES`, and `PF_TOOLS`. Registry entries may use `${CONST}/relative/path`, while project `.pf/` snapshots keep only ids, `path_ref`, load policy, and metadata.

`package_roots` follows the same privacy rule: the workplace may know absolute
or host-specific locations, while public project snapshots only keep the root
id and relative package/resource references.

This keeps the three surfaces separate:

- project-local `.pf/` state;
- ProcessForge distribution files in the repository root;
- private/global workplace infrastructure outside the project.
