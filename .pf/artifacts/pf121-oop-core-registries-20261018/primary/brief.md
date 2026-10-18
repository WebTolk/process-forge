# Package paths, platform selection, update registries and process contracts

Baseline `a32c4828fee3a10988026007f8a9089bfcebc226`: ninth slice identically delivered to both dev remotes, six current Works terminal/root doctor PASS, three no-product predecessors terminal-cancelled. Product/index clean. All nine original architecture documents reread; project context fresh/ready/continue. Sequential primary + four disjoint native contributors, then independent reviewer. Efforts packages/platform/contracts/review high, updates medium. No nested agents.

PF interface: use existing source CLI `python -B -X utf8 tools/processforge.py` only when an exact PF read is needed, with your prepared run/assignment/context. The installed MCP is not this source checkout interface and is not used or repaired. No MCP connection/bootstrap/context rebuild, online documentation or infrastructure action is needed. All required architecture, verified PF Python excerpts and concrete dependency before-images are explicitly declared inputs. Empty knowledge-resource grants do not authorize external bodies; the declared Python project input is available fulltext.

Preserve external 1.2.0 behavior, actual identities/access/guard/check/refusal/read order, unknowns, aliases and current I/O. D01/D02/D03/D06/D09/D11 and touched R01-R12 remain within existing scope. No new functionality, permission, DI/Kernel/plugin/cache, or MCP-resource development. Existing authoring preflight callbacks return to legacy and are intentionally not selected; transaction/lifecycle/lock/journal/recovery/installed-version writing remain explicitly legacy. Existing MCP registry metadata is only read as before.

Ownership:
```json
{
  "packages": [
    "src/processforge_core/resources/project_packages.py"
  ],
  "platform": [
    "src/processforge_core/project/platform_selection.py",
    "src/processforge_core/documents/answers.py",
    "src/processforge_core/documents/reader.py",
    "src/processforge_core/project/classification.py",
    "src/processforge_core/common/values.py",
    "src/processforge_core/project/platforms.py"
  ],
  "updates": [
    "src/processforge_core/maintenance/registries.py",
    "src/processforge_core/maintenance/documents.py"
  ],
  "contracts": [
    "src/processforge_core/process_catalog/contracts.py",
    "src/processforge_core/process_catalog/service.py"
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
    "existing": true,
    "methods": {
      "package_root_entries": "root_entries",
      "resolve_package_root": "resolve_root",
      "package_path_candidates": "path_candidates",
      "resolve_package_path": "resolve_path",
      "find_workplace_package_manifests": "find_manifests",
      "load_workplace_package_manifest": "load_manifest"
    }
  },
  "platform": {
    "class": "ProjectPlatformSelectionService",
    "module": "project/platform_selection.py",
    "methods": {
      "selected_project_platforms": "selected",
      "platform_contract_project_type_hints": "project_type_hints",
      "platform_contract_parent_type_hints": "parent_type_hints",
      "workplace_platform_ids_for_project_type": "ids_for_project_type",
      "platform_ids_from_detection_rules": "detected_ids",
      "platform_resource_findings": "resource_findings",
      "platform_binding_matches": "binding_matches",
      "optional_platform_resource_warnings": "optional_warnings",
      "forbidden_base_technology_platform_reference": "forbidden_base_reference",
      "available_platform_contract_records": "available_records"
    }
  },
  "updates": {
    "class": "UpdateRegistryReader",
    "module": "maintenance/registries.py",
    "methods": {
      "update_entity_manifest_records": "entities",
      "update_site_overrides": "overrides",
      "installed_subjects_by_key": "installed_subjects",
      "update_install_path": "install_path"
    }
  },
  "update_paths": {
    "class": "UpdateDocumentReader",
    "module": "maintenance/documents.py",
    "existing": true,
    "methods": {
      "update_runtime_root": "runtime_root",
      "update_candidates_path": "candidates_path",
      "update_notifications_path": "notifications_path"
    }
  },
  "contracts": {
    "class": "ProcessContractValidationService",
    "module": "process_catalog/contracts.py",
    "methods": {
      "validate_process_contract": "validate"
    }
  },
  "routes": {
    "class": "ProcessRouteDocumentReader",
    "module": "process_catalog/contracts.py",
    "methods": {
      "process_routes_path": "path",
      "load_process_route_map": "read"
    }
  }
}
```

Special owners:
```json
{
  "answer_strings": "AnswersDocumentReader.strings",
  "normalize_hint": "project.classification.normalize_hint",
  "hint_matches": "project.classification.hint_matches",
  "load_policy_document": "YamlDocumentReader.policy(name, root=None, *, distribution_root)",
  "registry_ids": "common.values.registry_ids",
  "normalize_platform_id": "PlatformContractReader.normalize_id_pair",
  "process_catalog_metadata": "existing canonical process_catalog.service.process_catalog_metadata",
  "process_is_public_stable": "process_catalog.service.process_is_public_stable"
}
```

Distribution-bound new constructors: ProjectPlatformSelectionService(distribution_root), UpdateRegistryReader(distribution_root), ProcessContractValidationService(distribution_root); route reader has concrete no-I/O defaults and project supplied per operation. Existing constructors/fields remain unchanged. YamlDocumentReader.policy has the one explicitly planned extra required keyword-only distribution_root: this replaces the old global ROOT and avoids a dummy captured project or one-method facade class. No first-class load_policy_document references exist; parent rewrites all seven calls with ROOT.

Required original architecture:

- `.pf/artifacts/original-architecture-alignment-20261010/migration-contract.md`
- `.pf/artifacts/progressive-oop-boundary-20261010/decision.md`
- `.pf/artifacts/oop-refactor-clarification-20261005/clarification.md`
- `.pf/artifacts/pf-framework-architecture-20261005/adr.md`
- `.pf/artifacts/pf-framework-architecture-20261005/domain.md`
- `.pf/artifacts/pf-framework-architecture-20261005/direction.md`
- `.pf/artifacts/python-framework-20261005/oop-02.md`
- `.pf/artifacts/python-framework-20261005/oop-03.md`
- `.pf/artifacts/python-framework-20261005/oop-05.md`

Verified Python material: `.pf/artifacts/pf121-oop-core-registries-20261018/primary/python-material.md`; full provenance is a declared adjacent input. Frozen actual dependency implementations are below. Read these immutable snapshots when learning interfaces, not a peer-owned mutable live file. Every code path is a declared output or exact reference; parent verifies final real imports after peers finish.

- `src/processforge_core/resources/snapshot.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__resources__snapshot.py.txt`
- `src/processforge_core/resources/project_packages.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__resources__project_packages.py.txt`
- `src/processforge_core/project/metadata.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__project__metadata.py.txt`
- `src/processforge_core/project/detection.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__project__detection.py.txt`
- `src/processforge_core/project/platforms.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__project__platforms.py.txt`
- `src/processforge_core/project/platform_policy.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__project__platform_policy.py.txt`
- `src/processforge_core/project/classification.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__project__classification.py.txt`
- `src/processforge_core/documents/answers.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__documents__answers.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__documents__reader.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/values.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__common__values.py.txt`
- `src/processforge_core/common/ids.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__common__ids.py.txt`
- `src/processforge_core/common/paths.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__common__paths.py.txt`
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__common__checks.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__work__context_documents.py.txt`
- `src/processforge_core/maintenance/documents.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__maintenance__documents.py.txt`
- `src/processforge_core/maintenance/sites.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__maintenance__sites.py.txt`
- `src/processforge_core/process_catalog/service.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__process_catalog__service.py.txt`
- `src/processforge_core/process_catalog/evolution.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__process_catalog__evolution.py.txt`
- `src/processforge_core/process_catalog/artifacts.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__process_catalog__artifacts.py.txt`
- `src/processforge_core/process_catalog/validation.py` => `.pf/artifacts/pf121-oop-core-registries-20261018/primary/inputs/processforge_core__process_catalog__validation.py.txt`

## packages

Extend EXISTING ProjectPackageCatalogReader with six mapped operations by REUSING exact WorkspacePathReferenceReader algorithms. Do not copy path/registry/ID rules. Main legacy uses public PackageRootResolution; existing canonical reader uses private _PackageRootResolution. Preserve public result type/name/repr/fields and alias identity through a narrow Core-to-Core record conversion; use a private conversion helper for new root/tuple/list results. The existing root_from_entry may share that same exact seven-field converter only; prove its sole intended factoring, preserving every other prior method/class field/constructor/model AST. Prove complete canonical method AST against frozen legacy with only self/call-owner/model-name normalization, plus exact conversion wrappers. Current legacy callee root_from_entry already became _project_package_catalog_reader.root_from_entry in prior wave: account for that when comparing canonical AST. Preserve read/write mode defaults, fallback/warnings/entry identity, order of root/path/manifest choices, ambiguity, containment, invalid IDs, soft/strict YAML and native failures. No new access rule or actual package mutation. Preserve original module future annotations, signatures/annotation strings except the explicitly declared policy distribution-root binding, native failures/messages/causes, guard/order/truthiness, mutations/aliases, current reads and unknown fields. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callbacks/providers/Any facade, no new capabilities/permissions/DI/Kernel/plugin framework, caches, permanent tests, live fixture/suite execution, Git mutation/remotes/infra/lifecycle operations or nested agents. Use exact valid prepared identity/scope and source CLI only when a PF read is needed; installed MCP is not this source interface and is not to be repaired. Read all explicit architecture/Python/frozen dependency inputs. Report complete normalized AST/signature/annotation/class-preservation proof, at most five useful synthetic cases, final raw SHA and Russian report. Parent executes actual assembled imports/live fixtures/existing affected checks. Every written file ends in exactly one newline.

## platform

Create ProjectPlatformSelectionService(distribution_root: Path) with ten mapped platform/registry selection/findings methods. Use concrete PlatformContractReader, ProjectDetectionService, ProjectPackageCatalogReader, AnswersDocumentReader, YamlDocumentReader and WorkspacePathReferenceReader; per-call real project/workplace roots, no dummy root. Extend EXISTING AnswersDocumentReader with exact recursive strings; EXISTING PlatformContractReader with exact normalize_id_pair; append exact normalize_hint/hint_matches to EXISTING project.classification and registry_ids to EXISTING common.values. Preserve all prior definitions/data/classes/constructors. Extend EXISTING YamlDocumentReader with policy(name: str, root: Path|None=None, *, distribution_root: Path)->dict[str,Any]: exact old policy algorithm, ROOT becomes required explicit keyword, self.load replaces canonical load_yaml_document. Constructor/fields and previous methods unchanged; parent rewrites every actual policy CALL to pass ROOT, no first-class references exist. In new selection service pass self.distribution_root explicitly. Normalize only this extra typed dependency for annotation/signature proof. Preserve raw answer flatten order, normalized hint variants/call counts, derived/parent type logic, registry literal statuses/aliases, detection order, required/recommended findings, forbidden-base policy and native errors. Existing MCP registry metadata only, no MCP resource invocation/new endpoint. Preserve original module future annotations, signatures/annotation strings except the explicitly declared policy distribution-root binding, native failures/messages/causes, guard/order/truthiness, mutations/aliases, current reads and unknown fields. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callbacks/providers/Any facade, no new capabilities/permissions/DI/Kernel/plugin framework, caches, permanent tests, live fixture/suite execution, Git mutation/remotes/infra/lifecycle operations or nested agents. Use exact valid prepared identity/scope and source CLI only when a PF read is needed; installed MCP is not this source interface and is not to be repaired. Read all explicit architecture/Python/frozen dependency inputs. Report complete normalized AST/signature/annotation/class-preservation proof, at most five useful synthetic cases, final raw SHA and Russian report. Parent executes actual assembled imports/live fixtures/existing affected checks. Every written file ends in exactly one newline.

## updates

Create UpdateRegistryReader(distribution_root: Path) for four exact records/overrides/installed lookup/install path operations. Reuse UpdateDocumentReader, ProjectPackageCatalogReader.workplace_root_paths, WorkspacePathReferenceReader, UpdateSitePolicy, UPDATE_SUBJECT_TYPES and safe_id. Extend EXISTING UpdateDocumentReader with exactly runtime_root/candidates_path/notifications_path; preserve its constructor/fields and all prior methods/data. Preserve discovery order/glob groups and package-only seen set, record/subject filtering/defaults, unknown data aliases, last-wins keys, overrides alias/truthiness priority and install override/current-record/fallback order. Constructor performs no I/O; workplace supplied per operation. Actual installation, timestamped installed-version writing and update lifecycle remain explicitly legacy, untouched. Do not add clock or atomic-write semantics. Preserve original module future annotations, signatures/annotation strings except the explicitly declared policy distribution-root binding, native failures/messages/causes, guard/order/truthiness, mutations/aliases, current reads and unknown fields. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callbacks/providers/Any facade, no new capabilities/permissions/DI/Kernel/plugin framework, caches, permanent tests, live fixture/suite execution, Git mutation/remotes/infra/lifecycle operations or nested agents. Use exact valid prepared identity/scope and source CLI only when a PF read is needed; installed MCP is not this source interface and is not to be repaired. Read all explicit architecture/Python/frozen dependency inputs. Report complete normalized AST/signature/annotation/class-preservation proof, at most five useful synthetic cases, final raw SHA and Russian report. Parent executes actual assembled imports/live fixtures/existing affected checks. Every written file ends in exactly one newline.

## contracts

Create process_catalog/contracts.py with ProcessRouteDocumentReader.path/read and ProcessContractValidationService(distribution_root: Path). Reuse ProjectMetadataReader, YamlDocumentReader, ProcessEvolutionPolicy, ProcessArtifactDeclarationPolicy, ProcessAuthoringValidationService and canonical metadata/classification functions/constants. Move exact HANDOFF_MODES set here. Extend EXISTING process_catalog/service.py with exact process_is_public_stable predicate; preserve all prior module nodes/data/functions. process_catalog_metadata is ALREADY canonical in service.py: no copy/new wrapper. Parent removes its old monolith wrapper and unused classification alias/import and imports actual canonical functions. Preserve complete 135-line contract checks and order, hard/strict/stable truthiness, all warnings/refusals/deprecated fields, route loading/soft failures/default mutation, repeated is_file observations, transitions and companion/template precedence. No actual handoff/lifecycle/route-map validation or mutation moves in this slice. Preserve original module future annotations, signatures/annotation strings except the explicitly declared policy distribution-root binding, native failures/messages/causes, guard/order/truthiness, mutations/aliases, current reads and unknown fields. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callbacks/providers/Any facade, no new capabilities/permissions/DI/Kernel/plugin framework, caches, permanent tests, live fixture/suite execution, Git mutation/remotes/infra/lifecycle operations or nested agents. Use exact valid prepared identity/scope and source CLI only when a PF read is needed; installed MCP is not this source interface and is not to be repaired. Read all explicit architecture/Python/frozen dependency inputs. Report complete normalized AST/signature/annotation/class-preservation proof, at most five useful synthetic cases, final raw SHA and Russian report. Parent executes actual assembled imports/live fixtures/existing affected checks. Every written file ends in exactly one newline.

## Primary and assurance

Remove 34 old function definitions, one already-canonical metadata wrapper included. Move HANDOFF_MODES and remove the now-unneeded PROCESS_CATALOG_CLASSIFICATIONS alias and unused import alias. Rename the existing canonical metadata import to its real name and import the new canonical stable predicate. Map actual remaining callers to owning methods/functions; policy calls get explicit distribution_root=ROOT through the already-concrete ContextContractInputs.documents. Existing _AnswersDocumentReader().strings serves answer consumers; do not create a facade wrapper. Migrate the one existing platform-selection smoke to the concrete selection owner without losing assertions. No other transport consumer was found by whole src/tools AST scan.

Preflight all primary edits in memory before writes. Complete old/new algorithms, previous-owner data/class preservation and actual annotations; source-only real default/copied Core imports, a few live root/registry/route/selection cases and existing affected smokes. All proof receipts bind final raw hashes. No permanent tests, repeated successful fixtures, broad Runtime/scheduler/recovery/release/archive/install/connected-host or ZIP checks. Reviewer pins exact final hashes before source-only commit and dual push/readback; token-only GitVerse, credential helper disabled. Preserve all unrelated source/.pf/index state. Complete six native Works/root doctor and reread architecture before the next scope. No new admission after device 2026-10-19 09:00; finish current tasks then report.
