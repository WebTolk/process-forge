# Core output paths, detection, environment and schema checks

Baseline: `8b1b122ddaecb755c702f515eafbaf171ef1590f`. Previous slice delivered to both dev remotes; all six Works terminal and root doctor passed. Original architecture fully reread; context fresh and ready. Source-only sequential 1-1-4 cycle. Primary alone owns caller/Host/docs/inventory integration. Four native shell writers own disjoint files; reviewer follows final assurance. All four contain subtle path, live-I/O, recursive/native-error or secret-environment contracts and use high reasoning; no nested agents.

Keep released 1.2.0 behavior: exact algorithms/signatures/defaults/actual future annotations, guard/error/refusal ordering, mutations/unknowns, current reads and identity/access. Core -> concrete Core/primitives only, no backward path. Reuse existing owners and canonical values; no DI/Kernel/plugin, new schema engine, permissions, features or MCP resources. D01/D02/D03/D06/D09/D11 and D07/R01-R12 keep existing scope. Pure rules may retain native legacy SystemExit during behavior-preserving extraction. No lifecycle/authorization/process startup/storage/recovery change.

Ownership:
```json
{
  "outputs": [
    "src/processforge_core/work/outputs.py"
  ],
  "platform": [
    "src/processforge_core/project/detection.py",
    "src/processforge_core/common/values.py"
  ],
  "environment": [
    "src/processforge_core/runtime/environment.py"
  ],
  "schema": [
    "src/processforge_core/maintenance/schema_checks.py"
  ],
  "review": []
}
```

API mapping:
```json
{
  "outputs": {
    "class": "WorkOutputPolicy",
    "module": "work/outputs.py",
    "methods": {
      "parse_required_output_waivers": "waivers",
      "project_output_path": "path",
      "task_output_path": "task_path",
      "expected_report_artifact": "expected_report",
      "default_expected_report_artifact": "default_report"
    }
  },
  "platform": {
    "class": "ProjectDetectionService",
    "module": "project/detection.py",
    "methods": {
      "list_project_files": "files",
      "detection_group_matches": "group_matches",
      "platform_detection_matches": "matches"
    }
  },
  "environment": {
    "class": "WorkerEnvironmentPolicy",
    "module": "runtime/environment.py",
    "methods": {
      "minimal_platform_environment": "minimal",
      "build_worker_environment": "build",
      "materialize_worker_launch_environment": "materialize",
      "expand_runtime_value": "expand"
    }
  },
  "schema": {
    "class": "UpdateSchemaChecks",
    "module": "maintenance/schema_checks.py",
    "methods": {
      "update_schema_type_matches": "type_matches",
      "update_resolve_schema_ref": "resolve_ref",
      "validate_update_instance_against_schema": "validate",
      "append_json_schema_checks": "append",
      "require_json_schema_document": "require"
    }
  }
}
```

## outputs

Implement exactly the five mapped existing algorithms in WorkOutputPolicy. Default concrete ContextContractInputs for path normalization; reuse common.ids.safe_id, common.values.as_list and pathlib. Preserve signatures/defaults, exact traversal/drive/colon/NUL/absolute guards and messages before resolve, symlink containment and native errors. Preserve no-path early returns, caught OSError/ValueError only, waiver last-write/order/truthiness, existing report defaults. No extra validation or file cache. The actual required_output_checks function stays legacy and will call new Core path policy. Main removes normalize_required_outputs obsolete wrapper and migrates its consumers to existing ContextContractInputs; do not duplicate it. Own only assigned product paths. Preserve original future annotations in every new implementation module. No monolith/CLI/Host back import, callback/provider or Any-core adapter. No Git mutations, remote access, infrastructure actions, lifecycle transitions, nested agents, permanent tests or fixture suites. Bounded compile/AST comparison is enough for contribution; primary owns callers and final focused assurance. Read frozen baseline/brief/Core AGENTS and exact Work state. Report actual file hashes and residual limitations in Russian report.md.

## platform

Implement exactly files/group_matches/matches in ProjectDetectionService and append exact list_value to EXISTING common.values, preserving its prior functions byte-for-byte. Import canonical path_matches_pattern and rel, no duplicated matcher. Preserve ignored components, relative sorting, direct-child directory distinctions, eager group evaluation, detection rule order, file_contains malformed entries, first-200 file order, full read then 200000-character truncation, invalid regex literal fallback and legacy already-matched break behavior. Constructor performs no I/O, each call observes current files. This is generic platform detection; classifier inventory and its exclusions stay unchanged. Own only assigned product paths. Preserve original future annotations in every new implementation module. No monolith/CLI/Host back import, callback/provider or Any-core adapter. No Git mutations, remote access, infrastructure actions, lifecycle transitions, nested agents, permanent tests or fixture suites. Bounded compile/AST comparison is enough for contribution; primary owns callers and final focused assurance. Read frozen baseline/brief/Core AGENTS and exact Work state. Report actual file hashes and residual limitations in Russian report.md.

## environment

Implement four mapped methods in WorkerEnvironmentPolicy with exact original environment/recursive expansion behavior. Import RESERVED_WORKER_ENV_KEYS from existing runtime.drivers canonical data; do not copy. Preserve Windows minimal allowlist and platform branching, sorted reserved-name refusal, PF-owned names and types, inherit truthiness, explicit configured expansion and str coercion, unsupported-placeholder errors, list-item str coercion, dict key behavior and alias returns. Inherited host environment is materialized only in materialize, never persisted by build. Do not inspect, print, save or include real host credentials/environment in proof. No subprocess or process-launch behavior moved. Use synthetic environment only for any bounded check. Own only assigned product paths. Preserve original future annotations in every new implementation module. No monolith/CLI/Host back import, callback/provider or Any-core adapter. No Git mutations, remote access, infrastructure actions, lifecycle transitions, nested agents, permanent tests or fixture suites. Bounded compile/AST comparison is enough for contribution; primary owns callers and final focused assurance. Read frozen baseline/brief/Core AGENTS and exact Work state. Report actual file hashes and residual limitations in Russian report.md.

## schema

Implement exact existing five-method JSON Schema subset in UpdateSchemaChecks(distribution_root: Path). Constructor only stores explicit distribution root, no I/O/cache. Existing validate recursion/refs/oneOf/anyOf/allOf/errors/order/native exceptions remain exact; do not replace with new schema engine or add features. Use canonical common Check/check. append reads distribution_root/schemas/schema_name fresh, same catch boundaries and diagnostic messages; require keeps SystemExit failure aggregation. Real update/source registry and installation behavior remain legacy. Preserve from __future__ import annotations. Own only assigned product paths. Preserve original future annotations in every new implementation module. No monolith/CLI/Host back import, callback/provider or Any-core adapter. No Git mutations, remote access, infrastructure actions, lifecycle transitions, nested agents, permanent tests or fixture suites. Bounded compile/AST comparison is enough for contribution; primary owns callers and final focused assurance. Read frozen baseline/brief/Core AGENTS and exact Work state. Report actual file hashes and residual limitations in Russian report.md.

## Integration and assurance

Remove all nineteen mapped old definitions; list_value is canonical in common.values, normalize_required_outputs reuses existing ContextContractInputs. Keep required_output_checks and actual worker process builder/worker paths legacy with new concrete dependencies. Do not migrate ProcessExecutionService optional output capability or prepared state/recovery. All known actual callers in monolith, work/context.py, Host and eight affected smokes are primary-owned. Existing test monkeypatches follow canonical owner, preserving assertions and early refusal/spy coverage; no obsolete aliases. Host imports remain lazy after existing bootstrap/guards and use concrete policies at prior call sites; no auth/provenance/attempt changes.

Primary temporarily compares old/new pure rules, path guard/native errors, annotation maps, aliases/check-list mutation, synthetic worker environments and current schema/platform file changes including same-size/same-mtime. Direct/copied normal Core imports must work without CLI/Host. Run only affected existing smokes on final bytes, retain successful outputs; no broad release/archive/install/Runtime/connected-host or ZIP-content checks. Symlink limitations reported as unavailable, no environment/ACL workarounds. Reviewer inspects final bytes and pins all product hashes. Update EN/RU owner docs and only changed/new checksum rows, preserving unrelated drift.

Commit only exact owned paths and portable proof; preserve unrelated index/work. Push identical commit to both origin/dev and gitverse/dev and read full SHA from both. GitVerse uses existing GITVERSE_TOKEN, credential helper disabled, never expose/store token. Complete all six native Works and root doctor; reread original architecture before next bounded scope. Source-only acceptance does not close OOP epics or qualify later layers. Stop admitting tasks at 2026-10-19 09:00 device time, finish current tasks and report the night.
