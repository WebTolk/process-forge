# Python Refactor Candidate Audit

Date: 2026-08-23

## Constraints

- Refactor only after baseline gates.
- Preserve CLI names, MCP tool names, JSON/YAML contracts, file layout, exit
  codes, and snapshot/search semantics.
- Do not touch Runtime lifecycle without a reproduced defect.
- Do not create `Utils`, `Helpers`, `CommonManager`, or a broad
  `ProcessForgeService`.

## Candidates

### ResourceSearchIndex

- Existing owner: `src/processforge_core/local_resource_search.py`.
- Used by: CLI search-index commands, MCP `pf.search`, `pf.session_context`,
  project-init/search smokes.
- Contract: project root + snapshot + optional workplace root determine status,
  refresh, rebuild, dirty marking, maintenance tick, and search.
- Coverage: `smoke_project_init_local_search_mcp`,
  `smoke_resource_indexing_policy_acceptance`,
  `smoke_search_update_operational_hardening`,
  `smoke_project_init_acceptance`, MCP/session smokes.
- Risk: low, if compatibility functions remain and adapters call the service.
- Decision: selected.

### ProjectInitializationService

- Existing owner: `src/processforge_core/project_initialization.py`.
- Already separated from the CLI as functional application service.
- Risk: low, but less immediate duplication remains in adapters.
- Decision: defer; do not refactor two slices unless release gates stay green
  with surplus validation time.

### Runtime Lifecycle

- Existing owner: `tools/pf_runtime/service.py` and host code.
- Risk: higher; lifecycle semantics are sensitive and already covered by
  long-lived runtime smokes.
- Decision: out of scope for 1.1.0 prerelease refactor.
