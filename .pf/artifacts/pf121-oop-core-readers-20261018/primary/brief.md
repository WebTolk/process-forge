# Work paths, worker command composition and live platform/update readers

Baseline: `585e1ec20e63339a0433dc5a53871cf567d98b3b`. Prior slice delivered to both dev remotes; all six Works terminal and root doctor passed, product/index clean. All nine original architecture/spec documents reread and context confirmed fresh/ready. Sequential 1-1-4 cycle: primary owns one caller/Host/docs/inventory scope, four native Core writers own separate files, independent reviewer follows completed implementation and final focused assurance. Paths medium; command/platform/documents/review high, according to complexity. No nested agents.

Preserve released 1.2.0 external CLI/MCP/protocols/errors/formats, all existing algorithms/defaults/actual annotations, unknowns/references/order/current reads and identity/access. Dependency direction monolith/transports -> owning concrete Core -> Core/stdlib only, no reverse import/provider/callback/Any-core. Reuse ready owners; no Kernel/DI/plugin, permissions, new features or MCP resources. D01/D02/D03/D06/D09/D11 and D07/R01-R12 retain existing boundaries. Lifecycle, access/admission, locks/journals/atomicity/recovery and process launch remain with their actual existing owners.

Ownership:
```json
{
  "paths": [
    "src/processforge_core/work/paths.py"
  ],
  "command": [
    "src/processforge_core/runtime/command.py"
  ],
  "platform": [
    "src/processforge_core/project/platforms.py"
  ],
  "documents": [
    "src/processforge_core/maintenance/documents.py"
  ],
  "review": []
}
```

API mapping:
```json
{
  "paths": {
    "class": "WorkPaths",
    "module": "work/paths.py",
    "methods": {
      "run_root": "run_root",
      "run_yaml_path": "run_document",
      "assignment_yaml_path": "assignment_document",
      "task_artifacts_root": "task_artifacts",
      "run_summary_path": "summary",
      "run_handoff_path": "handoff",
      "worker_prompt_path": "worker_prompt",
      "agent_run_root": "agent_run",
      "worker_run_paths": "worker_run"
    }
  },
  "command": {
    "class": "WorkerCommandBuilder",
    "module": "runtime/command.py",
    "methods": {
      "build_worker_process_command": "build",
      "worker_sandbox_for_task": "sandbox"
    }
  },
  "platform": {
    "class": "PlatformContractReader",
    "module": "project/platforms.py",
    "methods": {
      "platform_contract_id": "contract_id",
      "platform_contract_registry_entry": "registry_entry",
      "seed_platform_contract_paths": "seed_paths",
      "project_platform_contract_paths": "project_paths",
      "platform_contract_record": "record",
      "platform_contract_manifest_index": "index",
      "load_platform_contract": "load"
    }
  },
  "documents": {
    "class": "UpdateDocumentReader",
    "module": "maintenance/documents.py",
    "methods": {
      "update_registry_file": "registry_file",
      "update_source_registry_path": "source_registry",
      "installed_subjects_registry_path": "installed_registry",
      "update_site_overrides_path": "overrides_path",
      "derived_installed_update_sites_path": "derived_sites_path",
      "load_update_yaml": "yaml",
      "load_doctor_yaml": "doctor_yaml",
      "update_manifest_candidates_under": "manifest_candidates",
      "update_resolved_registry_paths": "registry_paths",
      "load_update_index": "index",
      "file_url_to_path": "file_url_path",
      "load_yaml_or_json_document": "document",
      "load_yaml_or_json_text": "text"
    }
  }
}
```

## paths

Create WorkPaths with exactly nine mapped existing path algorithms using concrete ProjectMetadataReader(project_root).flow_root() and canonical safe_id. Constructor performs no I/O and retains no current project/Work. Preserve repeated-hyphen valid run IDs in run_root/handoff, their distinct behavior from safe_id in agent/task paths, exact normalization/call order, output dictionary ordering and relative/absolute Path behavior. Do not substitute ContextContractInputs.assignment_path: it is deliberately strict while this legacy assignment path normalizes with safe_id. Do not add validation, containment, filesystem reads or new policy. Preserve from __future__ import annotations and actual annotation maps. Own only assigned product paths and your role artifacts/scratch. No Git mutation, remote access, lifecycle transitions, infrastructure changes, nested agents, permanent tests or fixture suite. Read exact valid Work, frozen baseline, brief and Core AGENTS. Use complete normalized AST/signature/annotation comparison; optionally 3-5 meaningful pure synthetic cases, no redundant matrix. Main handles real callers/imports and affected existing smokes. Report in Russian with final raw hashes and limitations.

## command

Create WorkerCommandBuilder(distribution_root: Path) with exact sandbox/build algorithms. Compose concrete WorkPaths, WorkOutputPolicy, WorkerEnvironmentPolicy, RuntimeDriverDefinitionPolicy and ContextContractInputs; no monolith callback or duplicated rules. WorkPaths is provided by the parallel paths contributor at its frozen API; do not read a partially written file or edit it. Compile/AST before it is available; primary does final imports. Preserve all field/key/guard/error/order semantics, model/reasoning normalization using existing ContextContractInputs, output-path preflight before variable construction, stdout/stderr/heartbeat resolution, placeholder/model_args/env ordering, prepared wrapper refusal and argv shape, driver_ref/limits and aliases. ROOT becomes explicit distribution_root, sys.executable remains current stdlib value. Actual process launch, locks, durable attempt state and lifecycle remain legacy. The two old normalize_agent_model/reasoning wrappers are already canonical and main removes them; do not duplicate. Never read/print/store real environment; any bounded case must use synthetic env. Preserve from __future__ import annotations and actual annotation maps. Own only assigned product paths and your role artifacts/scratch. No Git mutation, remote access, lifecycle transitions, infrastructure changes, nested agents, permanent tests or fixture suite. Read exact valid Work, frozen baseline, brief and Core AGENTS. Use complete normalized AST/signature/annotation comparison; optionally 3-5 meaningful pure synthetic cases, no redundant matrix. Main handles real callers/imports and affected existing smokes. Report in Russian with final raw hashes and limitations.

## platform

Create PlatformContractReader(distribution_root: Path) with exactly seven mapped algorithms. Reuse ContextContractInputs/YamlDocumentReader concrete YAML, canonical PROJECT_FLOW_ROOT and existing WorkspacePathReferenceReader for registry reads/relative resolution. Its existing implementations are exact matches for the old helper dependencies; do not copy or modify them. Instantiate references with explicit operation project/workplace roots (or explicit distribution root for irrelevant absent-project handle), never capture a current global project/Work. Preserve seed/project/workplace overlay order, duplicate overwrite position, glob groups/order, first registry alias, disabled/missing fallback, parse/error/empty handling, unknown fields and borrowed registry_entry/contract objects. No constructor I/O or parsed/metadata-only cache; all calls observe current documents. Hierarchy/resource/admission and activation remain legacy. Preserve from __future__ import annotations and actual annotation maps. Own only assigned product paths and your role artifacts/scratch. No Git mutation, remote access, lifecycle transitions, infrastructure changes, nested agents, permanent tests or fixture suite. Read exact valid Work, frozen baseline, brief and Core AGENTS. Use complete normalized AST/signature/annotation comparison; optionally 3-5 meaningful pure synthetic cases, no redundant matrix. Main handles real callers/imports and affected existing smokes. Report in Russian with final raw hashes and limitations.

## documents

Create UpdateDocumentReader(distribution_root: Path) with exactly thirteen mapped existing registry/path/document algorithms. Reuse concrete ContextContractInputs/YamlDocumentReader, WorkspacePathReferenceReader operation-local path constants/resolution and UpdateSchemaChecks(distribution_root). No copies of those helpers and no monolith callbacks. Preserve soft update YAML vs strict doctor YAML vs index behavior: index may return the YAML error sentinel; doctor appends schema errors but still returns the parsed mapping; update YAML filters errors to empty. Preserve existence/read ordering, registry override nonblank-string/type handling (without new trimming), path list duplicates/order/resolve, JSON only by suffix, text JSON->safe YAML fallback/catch boundaries, file-URL quirks and native errors. No constructor I/O/cache, network fetch, installation or writes. Current source commands keep their effects/guards. Preserve from __future__ import annotations and actual annotation maps. Own only assigned product paths and your role artifacts/scratch. No Git mutation, remote access, lifecycle transitions, infrastructure changes, nested agents, permanent tests or fixture suite. Read exact valid Work, frozen baseline, brief and Core AGENTS. Use complete normalized AST/signature/annotation comparison; optionally 3-5 meaningful pure synthetic cases, no redundant matrix. Main handles real callers/imports and affected existing smokes. Report in Russian with final raw hashes and limitations.

## Consumer closure and assurance

Primary removes all 33 old definitions and migrates every actual Name call and known external source consumer in egress/service.py, prepared/input.py, work/context.py, Host and seven smokes. Two model normalizers reuse existing ContextContractInputs directly. Source-only egress/prepared services keep other unmoved legacy dependencies; do not claim whole service independence. Existing prepared recovery terminal-admission test has a dynamic forbidden-name spy for build_worker_process_command: move this spy to WorkerCommandBuilder.build with the same assertion, never drop the terminal-before-build proof. Preserve all other assertions and guard/error ordering. Imports remain lazy at former guarded call sites where bootstrap requires it.

Use complete exact algorithm/retained-caller AST, actual annotations, direct/copied default Core composition and only affected existing smokes. A few focused live-read/command-shape cases cover new concrete wiring; do not add hundreds of redundant cases or permanent tests. Main owns fixture execution in its scratch, contributors do not rerun fixtures. Retain successful output; no full release/archive/install/Runtime/connected-host or ZIP-content checks. No environment/ACL/infrastructure repairs. Reviewer inspects final bytes and evidence without repeating suites.

Update EN/RU ownership reference and only affected/new checksum rows. Preserve known unrelated drift and dirty/index state. Commit exact owned files and portable proof; push one identical SHA to origin/dev and gitverse/dev and read back both full SHAs. GitVerse only existing GITVERSE_TOKEN with credential helper disabled, never expose/store it. Finish six native Works and one terminal root doctor, reread original architecture before another scope. Epics remain open; source-only acceptance does not qualify later layers. Stop admitting new tasks at 2026-10-19 09:00 device time, complete current tasks and report the night.
