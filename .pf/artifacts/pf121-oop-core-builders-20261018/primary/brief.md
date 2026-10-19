# Platform documents, registry checks, catalog audit and setup proposals

Baseline `9f576ce389afb518b7f869e28dc638dcdf1ef596`: eleventh slice delivered identically to both dev remotes, six exact Works terminal/root doctor PASS, product/index clean. All nine original architecture documents fully reread after delivery and current source context fresh/ready/continue. Primary + four disjoint native shell contributors, then independent clean-context reviewer. Registries/catalog/review high effort, platform/setup medium. No nested agents.

Use existing SOURCE CLI `python -B -X utf8 tools/processforge.py` with exact prepared identity if PF read is necessary. Do not use or repair installed connected MCP or infrastructure; no external documentation bodies or MCP resource development. Verified PF Python excerpts/provenance and immutable dependency before-images are explicit project sources.

Preserve released 1.2.0 contracts, touched D01/D02/D03/D06/D09/D11 and R01-R12. Transfer ownership of existing logic only. No permissions/DI/Kernel/plugin/cache/features, live workplace mutations, network, clocks or lifecycle/recovery changes. Platform semantic validation depends on legacy write-capable template/registry owners and remains deliberately outside this coherent read/builder slice.

Ownership:
```json
{
  "platform": [
    "src/processforge_core/project/platform_documents.py"
  ],
  "registries": [
    "src/processforge_core/project/registry_checks.py",
    "src/processforge_core/common/text.py"
  ],
  "catalog": [
    "src/processforge_core/process_catalog/audit.py",
    "src/processforge_core/process_catalog/service.py"
  ],
  "setup": [
    "src/processforge_core/project/setup.py"
  ],
  "review": []
}
```

APIs:
```json
{
  "platform": {
    "class": "PlatformDocumentBuilder",
    "module": "project/platform_documents.py",
    "methods": {
      "platform_entity_documents": "build"
    }
  },
  "registries": {
    "class": "WorkplaceRegistryValidationService",
    "module": "project/registry_checks.py",
    "methods": {
      "registry_path_resolution_checks": "paths",
      "package_root_registry_checks": "packages"
    }
  },
  "catalog": {
    "class": "BuiltinProcessCatalogAuditService",
    "module": "process_catalog/audit.py",
    "methods": {
      "builtin_process_catalog_report": "report",
      "package_process_index": "package_index"
    }
  },
  "setup": {
    "class": "WorkplaceSetupProposalBuilder",
    "module": "project/setup.py",
    "methods": {
      "render_workplace_setup_proposal": "build"
    }
  }
}
```

Shared standalone owners:
```json
{
  "ensure_trailing_newline": "common.text.ensure_trailing_newline",
  "check_with_hint": "common.text.check_with_hint",
  "process_catalog_contexts": "process_catalog.service.process_catalog_contexts"
}
```

All new constructors are cold and compose concrete existing owners; actual project/workplace roots are supplied per operation. Shared common/text.py belongs only to registries; platform uses that declared exact new API from baseline source and the parent assembles imports after all contributions finish. No peer-owned mutable live file is a required-source pin. The existing service.py may gain only process_catalog_contexts; all prior nodes/raw prefix remain intact.

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

Verified Python material/provenance are adjacent explicit inputs. Frozen concrete dependencies:
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__common__checks.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/values.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__common__values.py.txt`
- `src/processforge_core/common/ids.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__common__ids.py.txt`
- `src/processforge_core/common/paths.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__common__paths.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__documents__reader.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__work__context_documents.py.txt`
- `src/processforge_core/resources/snapshot.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__resources__snapshot.py.txt`
- `src/processforge_core/resources/project_packages.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__resources__project_packages.py.txt`
- `src/processforge_core/project/metadata.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__project__metadata.py.txt`
- `src/processforge_core/project/coordination.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__project__coordination.py.txt`
- `src/processforge_core/process_catalog/catalog_read.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__process_catalog__catalog_read.py.txt`
- `src/processforge_core/process_catalog/service.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__process_catalog__service.py.txt`
- `src/processforge_core/process_catalog/contracts.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__process_catalog__contracts.py.txt`
- `src/processforge_core/process_catalog/artifacts.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__process_catalog__artifacts.py.txt`
- `src/processforge_core/process_catalog/validation.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__process_catalog__validation.py.txt`
- `src/processforge_core/work/capsule_publication.py` => `.pf/artifacts/pf121-oop-core-builders-20261018/primary/inputs/processforge_core__work__capsule_publication.py.txt`

## platform

Create project/platform_documents.py PlatformDocumentBuilder() with build(target,values,contract,root_id), exactly the complete 136-line platform_entity_documents algorithm. Reuse common.yaml_io.dump_yaml and new declared common.text.ensure_trailing_newline; the registries peer owns that new shared primitive and its exact source is in baseline-functions. Preserve document path/byte/note list order, literal YAML/Markdown including escaped backslash-n sequences, insertion order of data keys, f-string/native KeyError behavior, references and encoding. Constructor no I/O; no actual file or authoring transaction effects. Do not call legacy ensure_trailing_newline or dump_yaml through Main; inspect frozen canonical YAML and readonly wrapper source to prove reuse. Preserve original future annotations, signatures and annotation strings, full algorithms, native errors/messages/causes, guard/check/read order, truthiness, aliases/unknowns and fresh reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/features, actual workplace writes/clock/network/lifecycle/recovery, permanent tests, Git mutations/remotes, infrastructure or nested agents. For PF reads use exact prepared identity and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed MCP is stale and is not used or repaired. Read all architecture/Python/frozen inputs. Prove complete normalized AST/signature/annotation/data/prior-owner preservation; compile without importing product modules; at most five useful synthetic cases from extracted definitions. Parent alone runs assembled imports/live fixtures/affected existing scripts. Russian report, final raw product SHA and proof.json, every file ends with exactly one newline.

## registries

Create project/registry_checks.py WorkplaceRegistryValidationService(distribution_root: Path), methods paths(workplace_root, workplace_manifest) and packages(workplace_root). Use existing WorkspacePathReferenceReader with actual workplace root and concrete ContextContractInputs/YamlDocumentReader, ProjectPackageCatalogReader(distribution_root), common checks and new shared formatting primitive. No dummy project root; path references bound to actual operation. Method packages must not collide with an instance field: name its concrete reader package_catalog. Preserve all 63/59 lines including registry specs iteration, alias/missing path behavior, status/writable/default truthiness, duplicate and warning/check order, actual current exists/is_dir observations. Existing canonical path algorithms must be reused, not copied. Create common/text.py with exact standalone ensure_trailing_newline and check_with_hint and future annotations; reuse unchanged common.checks.Check/check, preserving all hint text/newlines and native failures. Do not change prior checks module or fields. Parent changes the one actual composition callback from service.core.ensure_trailing_newline to the canonical function while retaining its deferred provider shape; other capsule publication dependencies remain unmigrated. Preserve original future annotations, signatures and annotation strings, full algorithms, native errors/messages/causes, guard/check/read order, truthiness, aliases/unknowns and fresh reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/features, actual workplace writes/clock/network/lifecycle/recovery, permanent tests, Git mutations/remotes, infrastructure or nested agents. For PF reads use exact prepared identity and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed MCP is stale and is not used or repaired. Read all architecture/Python/frozen inputs. Prove complete normalized AST/signature/annotation/data/prior-owner preservation; compile without importing product modules; at most five useful synthetic cases from extracted definitions. Parent alone runs assembled imports/live fixtures/affected existing scripts. Russian report, final raw product SHA and proof.json, every file ends with exactly one newline.

## catalog

Create process_catalog/audit.py BuiltinProcessCatalogAuditService(distribution_root: Path) with report(root,*,public=False) and package_index(root). Compose existing ProcessCatalogReadService(root, distribution_root=self.distribution_root).entries(strict=True) for actual per-operation root, plus concrete ProcessContractValidationService, ProcessAuthoringValidationService, ProcessArtifactDeclarationPolicy, YamlDocumentReader(_parse_simple_yaml) and canonical service metadata/stable functions. Read frozen Main _process_catalog_context/process_catalog_entries wrappers and canonical catalog_read.py to prove this normal binding is the same path. Preserve the entire ordered 87-line report, strict/public internal skip, official companion roots, repeated artifact/companion observations, counts, package checks, borrowed process fields and warning concatenation. package_index is deliberately the old flat sorted root/packages/*.yaml index, with YAML-error skip and last wins: do not replace it with the broader project package catalog. Append exact standalone process_catalog_contexts to EXISTING service.py, preserving its complete prior module AST/raw prefix/constructors/fields/methods and imports. No global current project or report cache. Preserve original future annotations, signatures and annotation strings, full algorithms, native errors/messages/causes, guard/check/read order, truthiness, aliases/unknowns and fresh reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/features, actual workplace writes/clock/network/lifecycle/recovery, permanent tests, Git mutations/remotes, infrastructure or nested agents. For PF reads use exact prepared identity and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed MCP is stale and is not used or repaired. Read all architecture/Python/frozen inputs. Prove complete normalized AST/signature/annotation/data/prior-owner preservation; compile without importing product modules; at most five useful synthetic cases from extracted definitions. Parent alone runs assembled imports/live fixtures/affected existing scripts. Russian report, final raw product SHA and proof.json, every file ends with exactly one newline.

## setup

Create project/setup.py WorkplaceSetupProposalBuilder() with build(session_id,answers), composing existing ProjectCoordinationReader() without I/O and canonical common.values.as_list/common.ids.safe_id. Read the frozen late Main as_list and canonical primitive to retain its runtime contract. Preserve entire 90-line proposal and Markdown model construction, placeholders/defaults, list coercions, truthiness, dict insertion order, borrowed resources/privacy/first_project aliases and native invalid mode refusal. Existing proposals and reports are returned as before, without file writes or a new approval/apply flow. Preserve original future annotations, signatures and annotation strings, full algorithms, native errors/messages/causes, guard/check/read order, truthiness, aliases/unknowns and fresh reads. Own only assigned source/artifact/scratch paths. No monolith/Host import or backwards callback/provider/Any facade, new permissions/DI/Kernel/plugin/cache/features, actual workplace writes/clock/network/lifecycle/recovery, permanent tests, Git mutations/remotes, infrastructure or nested agents. For PF reads use exact prepared identity and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed MCP is stale and is not used or repaired. Read all architecture/Python/frozen inputs. Prove complete normalized AST/signature/annotation/data/prior-owner preservation; compile without importing product modules; at most five useful synthetic cases from extracted definitions. Parent alone runs assembled imports/live fixtures/affected existing scripts. Russian report, final raw product SHA and proof.json, every file ends with exactly one newline.

## Primary, assurance and delivery

Remove all nine old definitions; actual calls use concrete builders/checkers/report owner or canonical shared functions. One composition lambda currently returns service.core.ensure_trailing_newline: import canonical common.text.ensure_trailing_newline and return that function from the same lambda; retain the deferred provider shape/timing contract and all other capsule dependencies. The self.ensure_trailing_newline call in capsule_publication.py is its existing injected provider and is distinct, unchanged. No other external source/tool consumers were found. Preflight all caller/docs changes before product writes.

Prove complete algorithms/signatures/annotations/aliases and unchanged prior service.py once in native contributions; primary proves full monolith and composition AST boundaries, actual default/copied Core and a few live registries/catalog/builder cases. Use affected existing scripts only, retain successful receipts, no permanent tests or broad Runtime/recovery/release/archive/install/connected-host/ZIP suites. Review uses exact manifest path/hash references and full AST privately, avoiding a redundant megabyte prompt capture without changing any read scope or budget. Preserve immutable reports, extract existing independent machine hash output for a narrative typo rather than repeat successful work.

Publish one accepted source commit to origin/dev and gitverse/dev with existing GITVERSE_TOKEN; credential helper and verbose tracing disabled, exact full SHA readback. Preserve unrelated dirty/index state. Complete six Works/root doctor, fully reread architecture and recheck source context before next scope. No new admission after device 2026-10-19 09:00; finish in-flight work and report.
