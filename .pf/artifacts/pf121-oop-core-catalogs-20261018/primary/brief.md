# Project package catalog, platform hierarchy, process semantics and worker plans

Baseline `3d5a01b10463ce119fc83bc513aff74386690816`: eight delivered source slices; latest SHA confirmed on both dev remotes, all six exact Works terminal and root doctor passed, product/index clean. All nine original architecture documents reread; PF context fresh/ready/continue. Source-only 1.2.0 behavior preservation, no MCP-resource development or infrastructure changes. Sequential primary + independent reviewer + four native workers. Packages/hierarchy/review high, semantics/workers medium by complexity.

Contracts D01/D02/D03/D06/D09/D11 and R01-R12 preserved within touched paths; no new Kernel/DI/plugin/permission framework or functionality. Existing process/lifecycle/locks/journals/recovery/Runtime start-stop owners unchanged. Do not confuse project package catalog with workplace search or public legacy root model with existing private snapshot model. Concrete Core-to-Core model conversion preserves the needed class representation without duplicating resolution rules.

Ownership:
```json
{
  "packages": [
    "src/processforge_core/resources/project_packages.py"
  ],
  "hierarchy": [
    "src/processforge_core/project/platform_resolution.py",
    "src/processforge_core/common/values.py"
  ],
  "semantics": [
    "src/processforge_core/process_catalog/semantics.py",
    "src/processforge_core/presentation/process_parity.py"
  ],
  "workers": [
    "src/processforge_core/runtime/worker_plans.py"
  ],
  "review": []
}
```

APIs:
```json
{
  "packages": {
    "class": "ProjectPackageCatalogReader",
    "module": "resources/project_packages.py",
    "methods": {
      "workplace_package_roots": "workplace_roots",
      "workplace_package_root_paths": "workplace_root_paths",
      "package_manifest_candidates": "candidates",
      "package_manifest_index": "index",
      "package_dependency_ids": "dependencies",
      "package_root_resolution_from_entry": "root_from_entry"
    }
  },
  "hierarchy": {
    "class": "PlatformContractResolver",
    "module": "project/platform_resolution.py",
    "methods": {
      "merge_id_list": "merge_ids",
      "resolve_platform_contracts": "resolve"
    }
  },
  "semantics": {
    "class": "ProcessSemanticPolicy",
    "module": "process_catalog/semantics.py",
    "methods": {
      "process_unsupported_fields": "unsupported_fields",
      "process_semantic_map": "map",
      "process_semantics": "describe",
      "compare_process_semantics": "compare",
      "sorted_strings": "strings",
      "event_emits": "events",
      "object_by_id": "objects"
    }
  },
  "parity_render": {
    "class": "ProcessParityRenderer",
    "module": "presentation/process_parity.py",
    "methods": {
      "render_process_import_report": "import_report",
      "render_process_parity_report": "parity_report"
    }
  },
  "workers": {
    "class": "WorkerPlanPolicy",
    "module": "runtime/worker_plans.py",
    "methods": {
      "worker_subagent_policy": "subagent_policy",
      "default_orchestrator_task_plan": "default_task_plan",
      "plan_worker_map": "worker_map",
      "task_dependency_ids": "task_dependency_ids",
      "task_dependencies_done": "task_dependencies_done",
      "worker_dependency_set": "dependency_set",
      "worker_depends_on": "depends_on",
      "plan_allows_write_scope_overlap": "allows_write_scope_overlap"
    }
  }
}
```

Special owner: common.values.parameter_payload; moved exact class PackageRootResolution in resources/project_packages.py; moved exact PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL in process_catalog/semantics.py. ProjectPackageCatalogReader and PlatformContractResolver take explicit distribution_root. No constructor performs I/O. Package index/candidates retain explicit project_root, distribution_root (including None), workplace_manifest arguments. Snapshot/path readers are concrete per-operation objects with real roots and matching document inputs.

## packages

Create ProjectPackageCatalogReader(distribution_root: Path) with six mapped operations and move exact @dataclass PackageRootResolution into the same Core module. Existing resources.snapshot._PackageRootResolution is a DISTINCT private representation; preserve that existing class and all snapshot code unchanged. Reuse WorkspacePathReferenceReader, ProjectMetadataReader, YamlDocumentReader(_parse_simple_yaml), OfficialProcessPackReader and common as_list/yaml_error. root_from_entry MUST reuse WorkspacePathReferenceReader.package_root_resolution_from_entry and convert its plain record into the moved public PackageRootResolution by seven explicit field references, preserving warnings/entry alias identity; do not duplicate path-resolution logic, rename/replace the existing private model or add a configurable factory. This Core-to-Core representation conversion preserves the legacy public model class name/repr/annotations/constructor; complete proof compares the reused canonical method against old algorithm plus exact field conversion. workplace_roots uses the actual manifest parent in concrete paths; no dummy project root or captured current Work. candidates uses bound distribution_root only where old ROOT was used; preserve explicit distribution_root parameter and None behavior, discovery/read/dedup/official-pack order. index is PROJECT last-wins plus duplicates sentinel, deliberately different from WorkplaceSearchCatalogReader first-wins; leave that reader unchanged. Constructor has no I/O; current project/workplace arguments per operation. Preserve exact original future annotations, bound signatures, errors/causes, messages, guard/read order, mutation/alias behavior, current reads and unknowns. Own only declared products/artifacts/scratch. No source CLI/Host import, monolith callback/provider/Any facade, caches, new feature/policy/DI framework, permanent tests, runtime or other infrastructure, Git/remote mutation, lifecycle transitions or nested agents. Read exact valid Work/capsule, original architecture/brief/Core AGENTS and frozen baseline; use PF Python knowledge. Provide complete normalized AST/signature/actual-annotation proof and at most five meaningful synthetic cases, final raw hashes and Russian report. Parent alone executes live fixtures and existing smokes after all contributions; do not repeat suites. New/changed files must end with exactly one newline.

## hierarchy

Create PlatformContractResolver(distribution_root: Path) with merge_ids and resolve, concrete PlatformContractReader, PlatformContractPolicy and the planned ProjectPackageCatalogReader. Move exact parameter_payload primitive into EXISTING common.values; preserve all previous module nodes/data/functions. Do not import any old package or parameter helper. Preserve nested resolve_one order, cycle strings, first traversal resource inclusion, required optional relationships, override object aliases, conflicts owner order, parameter alias return, package dependency FIFO and exact result insertion order/sorting. Package catalog is written by a disjoint native worker; use declared API from brief, do not edit or assume its early partial file complete. Full AST proof can be done without executing unfinished peer imports; parent verifies real default composition once both reports are collected. Preserve exact original future annotations, bound signatures, errors/causes, messages, guard/read order, mutation/alias behavior, current reads and unknowns. Own only declared products/artifacts/scratch. No source CLI/Host import, monolith callback/provider/Any facade, caches, new feature/policy/DI framework, permanent tests, runtime or other infrastructure, Git/remote mutation, lifecycle transitions or nested agents. Read exact valid Work/capsule, original architecture/brief/Core AGENTS and frozen baseline; use PF Python knowledge. Provide complete normalized AST/signature/actual-annotation proof and at most five meaningful synthetic cases, final raw hashes and Russian report. Parent alone executes live fixtures and existing smokes after all contributions; do not repeat suites. New/changed files must end with exactly one newline.

## semantics

Create ProcessSemanticPolicy with seven mapped methods and exact PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL data; create separate ProcessParityRenderer with exactly import_report and parity_report. Reuse canonical safe_id/rel/as_list/string_list/Check. Keep semantic projection and representation separate, preserve all Markdown strings/newlines, item overwrite/alias behavior, sorted-set conversion, source missing kind/scope exceptions, FAIL/WARN precedence, nested add ordering, exact unknown-field report and dictionaries. Parent removes nine old helpers/constant and migrates every real call in the same slice; no aliases. Preserve exact original future annotations, bound signatures, errors/causes, messages, guard/read order, mutation/alias behavior, current reads and unknowns. Own only declared products/artifacts/scratch. No source CLI/Host import, monolith callback/provider/Any facade, caches, new feature/policy/DI framework, permanent tests, runtime or other infrastructure, Git/remote mutation, lifecycle transitions or nested agents. Read exact valid Work/capsule, original architecture/brief/Core AGENTS and frozen baseline; use PF Python knowledge. Provide complete normalized AST/signature/actual-annotation proof and at most five meaningful synthetic cases, final raw hashes and Russian report. Parent alone executes live fixtures and existing smokes after all contributions; do not repeat suites. New/changed files must end with exactly one newline.

## workers

Create WorkerPlanPolicy with eight mapped operations, concrete ContextContractInputs for normalize_subagent_policy, WorkPaths and YamlDocumentReader(_parse_simple_yaml). task_dependencies_done uses existing strict documents.read, exact current assignment path/status reads and early False; no new availability or permission rules. Preserve map value alias identity, worker id normalization, default fixture plan literals, dependency union order, seen = seen or set() semantics, same shared recursion set, native errors and allow_write_scope_overlap is True identity. Do not modify worker execution, locks, scheduler, lifecycle, process start/stop or recovery. Preserve exact original future annotations, bound signatures, errors/causes, messages, guard/read order, mutation/alias behavior, current reads and unknowns. Own only declared products/artifacts/scratch. No source CLI/Host import, monolith callback/provider/Any facade, caches, new feature/policy/DI framework, permanent tests, runtime or other infrastructure, Git/remote mutation, lifecycle transitions or nested agents. Read exact valid Work/capsule, original architecture/brief/Core AGENTS and frozen baseline; use PF Python knowledge. Provide complete normalized AST/signature/actual-annotation proof and at most five meaningful synthetic cases, final raw hashes and Russian report. Parent alone executes live fixtures and existing smokes after all contributions; do not repeat suites. New/changed files must end with exactly one newline.

## Primary and assurance

Remove all 26 old function definitions, old public class definition and one constant assignment, import the actual canonical class where still used by unselected legacy functions, map every remaining Name/call to concrete owners or common parameter primitive, and migrate three work/context parameter consumers. The unchanged workplace search reader method with the same package_manifest_index spelling is not a legacy consumer. No blanket AST replacement of string literals or embedded fixtures. Preserve raw unrelated bytes, public payloads/refusal order/live reads and object aliases. All primary edits preflight in memory before writing. EN/RU ownership and only touched inventory rows updated.

Native complete AST/signature/annotation/data proofs; primary few live package/cycle/default dependency cases, direct/copied Core import and existing affected package/platform/process-parity/worker checks. No permanent tests, broad Runtime/recovery/release/archive/install/connected-host/ZIP checks. Preserve successful receipts and run only failed or unrun checks. Final independent review pins raw product hashes; only then exact commit/push both origin/dev and gitverse/dev, token-only GitVerse with credential helper disabled and no secret output. Close all six Works, root doctor, then reread the original architecture. Do not admit new tasks after device 2026-10-19 09:00; finish current scope and report.
