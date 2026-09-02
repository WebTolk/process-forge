# Real Project Resource Resolution Audit

Status: draft
Date: 2026-09-02
Scope: read-only audit of the current Joomla extension project context snapshot.

## Reproduction

`project-context-check` reports a fresh, ready snapshot for the real Joomla
extension project. Its platform is `joomla` and its knowledge stack contains
the generic Joomla core package, the Joomla 6.1 documentation package, the
administrator documentation package, and the Joomla toolkit package.

The snapshot's `context_requirements.knowledge_packages` contains every Joomla
core branch and explicit historical core version from v1 through v6. The
snapshot's `local_search_resources` is constructed from all available package
resources, so it includes historical platform sources even when the project
only needs the current platform line.

The documentation resource has metadata indexing. The source-tree resources
are also metadata indexed in this snapshot. Thus the current real project has
no authorized full-text documentation corpus and cannot return useful
documentation content from `pf.search`.

## Provenance Trace

1. The Joomla platform contract directly requires the generic core package and
   the Joomla 6.1 documentation packages.
2. The generic core package declares dependencies on every historical branch.
3. `resolve_platform_contracts` follows the complete package dependency
   closure and records each package as required.
4. `build_project_files` persists that closure in generated project context
   requirements.
5. `build_project_context_snapshot` copies all available package resources to
   `local_search_resources` instead of the selected resource set.
6. `local_resource_search._resource_records` additionally treats
   `available_knowledge_resources` as authorized.

## Finding

The defect is selection and authorization, not a missing Joomla package: the
resolver has no generic platform-version selection policy, and downstream
search expands the chosen project context back to the full available catalog.
The remediation must retain an auditable available catalog while deriving a
small selected set and restricting both resolve and search to it.

## Boundary

The audited external project and its workplace distribution were not modified.
Acceptance will use a controlled fixture based on its public context shape.
