# Worker plans, records, route/handoff documents and update validation

Baseline `76f3d8c90e874beabac438b7c0dfd1725c8e0628`: tenth slice delivered to both dev remotes with exact full SHA readback; transient GitVerse DNS failure resolved by retrying the same commit only on the missing remote. All six Works terminal/root doctor PASS; product/index clean. All nine original architecture inputs fully reread after delivery, source context fresh/ready/continue. Sequential primary + four disjoint native shell contributors, then independent clean-context reviewer. Worker plans and reviewer high effort; records/routes/updates medium. No nested agents.

Use the existing SOURCE CLI `python -B -X utf8 tools/processforge.py` with exact prepared selectors when PF read is necessary. Installed connected MCP is stale and is not used or repaired. No infrastructure bootstrap, external documentation bodies or new MCP resource work. All actual dependency before-images and verified PF Python excerpts are explicit immutable project inputs.

Preserve released 1.2.0 behavior and touched D01/D02/D03/D06/D09/D11 and R01-R12. No permission framework, new DI/Kernel/plugin/cache/features or changed JSON/YAML rules. Keep timestamped writes, network, archive, locks/journals/recovery, actual worker/handoff/hook/update execution at their existing owners. Read/path/semantic-check operations only.

Ownership:
```json
{
  "workers": [
    "src/processforge_core/runtime/worker_validation.py"
  ],
  "records": [
    "src/processforge_core/project/hooks.py",
    "src/processforge_core/common/record_validation.py"
  ],
  "routes": [
    "src/processforge_core/process_catalog/routes.py",
    "src/processforge_core/process_catalog/handoffs.py"
  ],
  "updates": [
    "src/processforge_core/maintenance/validation.py",
    "src/processforge_core/maintenance/documents.py",
    "src/processforge_core/maintenance/registries.py"
  ],
  "review": []
}
```

APIs:
```json
{
  "workers": {
    "class": "WorkerPlanValidationService",
    "module": "runtime/worker_validation.py",
    "methods": {
      "config_extension_key": "extension_key",
      "unsupported_config_keys": "unsupported_keys",
      "validate_subagent_policy_outputs": "subagent_outputs",
      "validate_orchestrator_task_plan": "validate"
    }
  },
  "hooks": {
    "class": "HookConfigurationReader",
    "module": "project/hooks.py",
    "methods": {
      "hook_config_path": "path",
      "validate_hooks_config": "validate"
    }
  },
  "records": {
    "class": "RecordValidationPolicy",
    "module": "common/record_validation.py",
    "methods": {
      "validate_event_object": "event",
      "validate_chat_message_object": "chat"
    }
  },
  "routes": {
    "class": "ProcessRouteService",
    "module": "process_catalog/routes.py",
    "methods": {
      "route_by_id": "by_id",
      "validate_process_route_map": "validate",
      "required_role_from_route": "required_role"
    }
  },
  "handoffs": {
    "class": "HandoffDocumentReader",
    "module": "process_catalog/handoffs.py",
    "methods": {
      "handoff_dir": "directory",
      "handoff_yaml_path": "path",
      "load_handoff": "read"
    }
  },
  "updates": {
    "class": "UpdateDocumentValidationService",
    "module": "maintenance/validation.py",
    "methods": {
      "validate_update_site_overrides_data": "site_overrides",
      "validate_normalized_update_manifest_data": "normalized_manifest"
    }
  },
  "update_registry": {
    "class": "UpdateRegistryReader",
    "module": "maintenance/registries.py",
    "existing": true,
    "methods": {
      "installed_subject_version_map": "installed_versions"
    }
  },
  "update_paths": {
    "class": "UpdateDocumentReader",
    "module": "maintenance/documents.py",
    "existing": true,
    "methods": {
      "staged_update_record_path": "staged_path",
      "read_staged_update_record": "staged_record"
    }
  }
}
```

Already canonical wrappers removed by primary:
```json
{
  "normalize_workspace_access": "existing ContextContractInputs.normalize_workspace_access",
  "normalize_subagent_policy": "existing ContextContractInputs.normalize_subagent_policy"
}
```

Six exact moved constants: ORCHESTRATOR_PLAN_TOP_LEVEL_KEYS, ORCHESTRATOR_PLAN_RUNTIME_KEYS, ORCHESTRATOR_PLAN_WORKER_KEYS, ORCHESTRATOR_PLAN_SUBAGENT_KEYS, EVENT_TYPE_PATTERN, SHA256_HEX_RE. The identical WORKSPACE_ACCESS_KEYS tuple already belongs to work.context_documents: remove the Main duplicate and import actual canonical data. Existing reader constructors/fields/prior methods remain unchanged. New constructors only assemble concrete owners without I/O, with actual project root passed at operation time.

Required architecture:
- `.pf/artifacts/original-architecture-alignment-20261010/migration-contract.md`
- `.pf/artifacts/progressive-oop-boundary-20261010/decision.md`
- `.pf/artifacts/oop-refactor-clarification-20261005/clarification.md`
- `.pf/artifacts/pf-framework-architecture-20261005/adr.md`
- `.pf/artifacts/pf-framework-architecture-20261005/domain.md`
- `.pf/artifacts/pf-framework-architecture-20261005/direction.md`
- `.pf/artifacts/python-framework-20261005/oop-02.md`
- `.pf/artifacts/python-framework-20261005/oop-03.md`
- `.pf/artifacts/python-framework-20261005/oop-05.md`

Python material/provenance are adjacent explicit inputs. Frozen concrete dependencies:
- `src/processforge_core/runtime/catalog.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__runtime__catalog.py.txt`
- `src/processforge_core/runtime/worker_plans.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__runtime__worker_plans.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__work__context_documents.py.txt`
- `src/processforge_core/work/scope_conflicts.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__work__scope_conflicts.py.txt`
- `src/processforge_core/project/metadata.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__project__metadata.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__documents__reader.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__common__checks.py.txt`
- `src/processforge_core/common/ids.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__common__ids.py.txt`
- `src/processforge_core/common/privacy.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__common__privacy.py.txt`
- `src/processforge_core/common/values.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__common__values.py.txt`
- `src/processforge_core/process_catalog/contracts.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__process_catalog__contracts.py.txt`
- `src/processforge_core/maintenance/schema_checks.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__maintenance__schema_checks.py.txt`
- `src/processforge_core/maintenance/source_contracts.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__maintenance__source_contracts.py.txt`
- `src/processforge_core/maintenance/documents.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__maintenance__documents.py.txt`
- `src/processforge_core/maintenance/registries.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__maintenance__registries.py.txt`
- `src/processforge_core/work/context.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__work__context.py.txt`
- `src/processforge_core/prepared/resources.py` => `.pf/artifacts/pf121-oop-core-audits-20261018/primary/inputs/processforge_core__prepared__resources.py.txt`

## workers

Create runtime/worker_validation.py with WorkerPlanValidationService(distribution_root: Path), four mapped methods and the exact four ORCHESTRATOR_PLAN_* sets. Use concrete ContextContractInputs, RuntimeDriverCatalogReader(distribution_root), WorkerPlanPolicy, ScopeConflictService(project_root), common safe_id/check and existing WORKSPACE_ACCESS_KEYS imported from work.context_documents, not copied. No-I/O constructor. extension_key and unsupported_keys retain exact algorithms. validate retains all 103 lines, literal type tests, repeated live driver IDs, conflict creation/call order and dependency exemptions. subagent_outputs retains live recursive file observations, containment prefix and max-count failures. Two old normalize_* functions are already canonical wrappers: do not copy them. Parent removes wrappers and redirects all actual monolith and three other Core call sites to ContextContractInputs. Parent imports shared WORKSPACE_ACCESS_KEYS for two surviving Main consumers. Preserve default/duplicate/dependency/write-conflict/read-scope/model/effort/extension behavior exactly. Preserve original future annotations, signatures and annotation strings, complete algorithms, native errors/messages/causes, guards/check/read/refusal order, truthiness, aliases/unknowns and current reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backward callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/functionality, clock/network/write/lifecycle behavior, permanent tests, Git mutation/remotes, infrastructure or nested agents. Use exact prepared identity and SOURCE CLI python -B -X utf8 tools/processforge.py if PF read is required; installed MCP is not this checkout and must not be repaired. Read required architecture/Python/frozen dependency inputs. Prove complete normalized AST/signature/annotation/data preservation, compile without imports, and at most five useful synthetic cases using extracted definitions. Do not execute actual assembled imports/live fixtures or suites; parent owns them. Russian report with final product raw SHA and machine-readable proof.json; every file ends with exactly one newline.

## records

Create project/hooks.py HookConfigurationReader() with path(project_root)/validate(project_root), concrete YamlDocumentReader(_parse_simple_yaml) and ProjectMetadataReader with actual operation-local project root. Reuse canonical flow-root selection; preserve missing/invalid/malformed hooks handling, list/field/event_types order and quoted wildcard messages. Create common/record_validation.py RecordValidationPolicy() with event/chat methods and exact EVENT_TYPE_PATTERN; reuse common.privacy.contains_secret_value and json.dumps ensure_ascii=False exactly. Preserve event/chat required-key order, mapping guards, default body and native JSON serialization failures. No hook dispatch/effects, journal, transports or schema expansion. Preserve original future annotations, signatures and annotation strings, complete algorithms, native errors/messages/causes, guards/check/read/refusal order, truthiness, aliases/unknowns and current reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backward callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/functionality, clock/network/write/lifecycle behavior, permanent tests, Git mutation/remotes, infrastructure or nested agents. Use exact prepared identity and SOURCE CLI python -B -X utf8 tools/processforge.py if PF read is required; installed MCP is not this checkout and must not be repaired. Read required architecture/Python/frozen dependency inputs. Prove complete normalized AST/signature/annotation/data preservation, compile without imports, and at most five useful synthetic cases using extracted definitions. Do not execute actual assembled imports/live fixtures or suites; parent owns them. Russian report with final product raw SHA and machine-readable proof.json; every file ends with exactly one newline.

## routes

Create process_catalog/routes.py ProcessRouteService(distribution_root: Path) with by_id/validate/required_role using existing ProcessRouteDocumentReader, exact shared HANDOFF_MODES from contracts, UpdateSchemaChecks(distribution_root) for existing generic schema append, common safe_id/check. No new schema engine or behavior. Preserve ID normalization, live route read order, borrowed returned route mapping, first match, native not-found SystemExit, duplicate checks and exact semantic check order. Create process_catalog/handoffs.py HandoffDocumentReader() with directory/path/read using actual ProjectMetadataReader(project_root), safe_id and YamlDocumentReader(_parse_simple_yaml). Preserve relative flow-root, suffixes/default IDs, soft YAML truthiness and not-found refusal. Only reads/paths move; save_handoff timestamp/write, actual handoff/leases/route execution/continuation lifecycle remain legacy. Preserve original future annotations, signatures and annotation strings, complete algorithms, native errors/messages/causes, guards/check/read/refusal order, truthiness, aliases/unknowns and current reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backward callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/functionality, clock/network/write/lifecycle behavior, permanent tests, Git mutation/remotes, infrastructure or nested agents. Use exact prepared identity and SOURCE CLI python -B -X utf8 tools/processforge.py if PF read is required; installed MCP is not this checkout and must not be repaired. Read required architecture/Python/frozen dependency inputs. Prove complete normalized AST/signature/annotation/data preservation, compile without imports, and at most five useful synthetic cases using extracted definitions. Do not execute actual assembled imports/live fixtures or suites; parent owns them. Russian report with final product raw SHA and machine-readable proof.json; every file ends with exactly one newline.

## updates

Create maintenance/validation.py UpdateDocumentValidationService(distribution_root: Path), composing existing UpdateSchemaChecks and UpdateSourceContractPolicy without I/O; exact site_overrides and normalized_manifest semantic checks, plus exact SHA256_HEX_RE. Preserve empty-document early refusal, schema append timing, nested loop/field/check order, truthiness, unknown fields, duplicate site checks, original/preserved environment checks, artifact URL shape/hash failures and PASS fallback. Extend EXISTING UpdateRegistryReader with installed_versions (distinct filter: type/id/version strings and nonempty version, last wins); preserve constructor/fields and every previous method/data. Extend EXISTING UpdateDocumentReader with staged_path/staged_record; preserve constructor/fields/all previous methods. Candidate ID is concatenated verbatim in old algorithm: do not add normalization/containment policy. Stage file reads remain soft-YAML current reads; no actual staging, installation, clock, mutation or archive work. Preserve original future annotations, signatures and annotation strings, complete algorithms, native errors/messages/causes, guards/check/read/refusal order, truthiness, aliases/unknowns and current reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backward callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/functionality, clock/network/write/lifecycle behavior, permanent tests, Git mutation/remotes, infrastructure or nested agents. Use exact prepared identity and SOURCE CLI python -B -X utf8 tools/processforge.py if PF read is required; installed MCP is not this checkout and must not be repaired. Read required architecture/Python/frozen dependency inputs. Prove complete normalized AST/signature/annotation/data preservation, compile without imports, and at most five useful synthetic cases using extracted definitions. Do not execute actual assembled imports/live fixtures or suites; parent owns them. Russian report with final product raw SHA and machine-readable proof.json; every file ends with exactly one newline.

## Primary and assurance

Remove all 21 old functions and seven old constant assignments; add owning imports/compositions and migrate every actual call. Reuse existing _context_contract_inputs, _update_registry_reader and _update_document_reader. Core work/context.py has two normalization calls, prepared/resources.py one; both already permit concrete ContextContractInputs and move exactly these calls, leaving all other legacy callbacks explicitly unmigrated. No external tool consumers were found. Preflight every primary edit before any product write. Update EN/RU ownership, including old historical full-validator/companion claims superseded by recent slices, and only touched inventory rows.

Contributors prove complete algorithms/data/signatures/prior owners once; primary proves full monolith and consumer AST changes, default/copied Core imports and a few real file/native failure observations. Run existing affected scripts only; retain successful receipts and recognize their actual output without reruns. No broad Runtime/scheduler/recovery/release/archive/install/connected-host/ZIP suites or permanent tests. Final product raw hashes are pinned before independent review; publish one exact source commit to origin/dev and gitverse/dev with existing token, credential helper disabled and no verbose Git tracing; preserve unrelated dirty/index state. Complete six Works/root doctor and fully reread original architecture before selecting another scope. No new admission after device 2026-10-19 09:00; finish current tasks then report.
