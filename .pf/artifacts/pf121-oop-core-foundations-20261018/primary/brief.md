# Registry writes, template catalog and platform validation

Baseline `d935e9bc981c85c4179eb91062c92eabe29ea92f`: twelfth slice delivered to both dev heads, six current Works terminal/root doctor PASS, cancelled predecessor retained. All nine original architecture inputs fully reread after delivery; context fresh/ready/continue and product/index clean. Sequential 1-1-4: primary + four disjoint native shell workers, then independent clean-context review. Efforts: registry/templates/semantics/review high; dependencies medium. No nested workers.

SOURCE CLI only for PF reads with exact prepared selectors. All architecture, Python excerpts and concrete dependencies are explicit required sources; no infrastructure actions, installed MCP use/repair, network or future MCP resource feature. External contract stays 1.2.0. D01/D02/D03/D06/D07/D09/D11 and applicable R01-R12 are preserved; no broad epic acceptance.

Ownership:
```json
{
  "registry": [
    "src/processforge_core/project/registry_write.py",
    "src/processforge_core/common/values.py"
  ],
  "templates": [
    "src/processforge_core/project/templates.py"
  ],
  "semantics": [
    "src/processforge_core/project/platform_validation.py",
    "src/processforge_core/common/policies.py"
  ],
  "dependencies": [
    "src/processforge_core/project/requirements.py"
  ],
  "review": []
}
```

Exact APIs:
```json
{
  "registry": {
    "class": "WorkplaceRegistryWriter",
    "module": "project/registry_write.py",
    "methods": {
      "upsert_registry_entry": "upsert"
    }
  },
  "templates": {
    "class": "TemplateCatalogService",
    "module": "project/templates.py",
    "methods": {
      "resolve_template_root": "resolve_root",
      "template_manifest_path": "manifest"
    }
  },
  "semantics": {
    "class": "PlatformContractValidationService",
    "module": "project/platform_validation.py",
    "methods": {
      "platform_contract_semantic_checks": "validate"
    }
  },
  "dependencies": {
    "class": "PlatformDependencyPreflightService",
    "module": "project/requirements.py",
    "methods": {
      "platform_dependency_preflight": "check",
      "registry_ids_from_workplace": "registry_ids"
    }
  }
}
```

Every service constructor takes only distribution_root: Path and composes concrete owners, without I/O. Actual workplace roots are operation parameters. Shared standalone functions:
```json
{
  "upsert_resource": "common.values.upsert_resource",
  "policy_entries": "common.policies.policy_entries",
  "policy_id_matches": "common.policies.policy_id_matches"
}
```

Canonical APIs were verified in actual source before admission; do not invent or assume a method. WorkspacePathReferenceReader(workplace_root,workplace_root,workplace_manifest=workplace_root/"workplace.yaml",inputs=ContextContractInputs()) provides workplace_path_resolution and path_resolution_to_path. ProjectPackageCatalogReader(root).find_manifests/index are actual prior owners. TemplateCatalogService calls WorkplaceRegistryWriter; semantics and preflight call TemplateCatalogService. No backwards edges. Registry/common.values belongs only to registry worker; common/policies belongs only to semantics. Peer declarations are pinned full original algorithms in baseline, not mutable peer source pins.

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

Frozen concrete dependency before-images:
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__checks.py.txt`
- `src/processforge_core/common/text.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__text.py.txt`
- `src/processforge_core/common/yaml_dump.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__yaml_dump.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/values.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__values.py.txt`
- `src/processforge_core/common/paths.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__common__paths.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__documents__reader.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__work__context_documents.py.txt`
- `src/processforge_core/resources/snapshot.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__resources__snapshot.py.txt`
- `src/processforge_core/resources/project_packages.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__resources__project_packages.py.txt`
- `src/processforge_core/project/metadata.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__project__metadata.py.txt`
- `src/processforge_core/project/platforms.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__project__platforms.py.txt`
- `src/processforge_core/project/platform_policy.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__project__platform_policy.py.txt`
- `src/processforge_core/project/platform_resolution.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__project__platform_resolution.py.txt`
- `src/processforge_core/project/platform_selection.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__project__platform_selection.py.txt`
- `src/processforge_core/maintenance/schema_checks.py` => `.pf/artifacts/pf121-oop-core-foundations-20261018/primary/inputs/processforge_core__maintenance__schema_checks.py.txt`

## registry

Create project/registry_write.py WorkplaceRegistryWriter(distribution_root: Path).upsert(path,collection_key,entry) from the complete original upsert_registry_entry. Compose existing ContextContractInputs or YamlDocumentReader(_parse_simple_yaml), canonical yaml_error/text/yaml_dump, UpdateSchemaChecks(distribution_root), json/os/uuid. ROOT becomes self.distribution_root. Preserve exactly the twelve registry-name/schema mappings, all fail-before-mutation guards, schema load/validate exception tuple and cause, errors[:8], parent mkdir, UUID stage name, same-parent write, os.replace and finally exists/unlink including its original failure precedence. Do not substitute a generic atomic writer, add fsync/locks/retries or change schema policy. Append exact standalone upsert_resource to existing common/values.py: full original module AST/raw prefix/imports unchanged, shared list identity and first matching replacement versus append return strings intact. No parameter/helper aliases back to Main. Prove full normalized algorithm, schema mapping and all prior values.py. Synthetic cases should cover successful added/updated plus refusal and staging/replace/cleanup ordering without real filesystem writes. Preserve future annotations, signatures/annotation strings, complete algorithms/literals, exact native errors and causes, guard/read/write/check order, unknowns, aliases, truthiness, borrowed values and fresh observations. Constructors are cold; distribution_root is explicit; actual workplace root is supplied per operation. No Main/Host imports, callbacks/providers/Any or ModuleType paths back to the monolith, duplicate existing path/parser/schema algorithms, new features/policies/caches/DI/framework or permission/lifecycle changes. No actual workplace writes; native characterization uses at most five synthetic cases with stub paths/I/O and extracted definitions. Parent alone performs bounded real scratch I/O, direct/copied Core imports and existing affected scripts. Own only declared files/artifacts/scratch; do not edit Main, docs, inventory or peer files. All peer APIs and full original algorithms are explicit in this brief/baseline; do not read a mutable peer file as a prepared input. Use exact PF selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed connected MCP is stale and must not be used/repaired. No Git mutations/remotes/infrastructure/nested agents/self lifecycle. Read original architecture, Python material and frozen concrete dependencies. Compile source without importing product modules. Produce Russian report.md and proof.json with schema described in brief, final raw hashes and exactly one final newline.

## templates

Create project/templates.py TemplateCatalogService(distribution_root: Path) methods resolve_root(workplace_root,template_root_id=None,*,mode="read") and manifest(workplace_root,template_id) from both complete originals. Compose concrete WorkplaceRegistryWriter(distribution_root), ContextContractInputs and existing WorkspacePathReferenceReader instantiated with actual workplace_root for both project_root/workplace_root plus workplace.yaml. Reuse workplace_path_resolution/path_resolution_to_path methods; do not copy their algorithms. The registry peer explicitly supplies project.registry_write.WorkplaceRegistryWriter.upsert with the original full algorithm pinned in baseline; no Main callback. Preserve fallback global ${PF_TEMPLATES} entry, write-mode upsert BEFORE selected-ID validation, available/first selection, path warnings/native behavior (do not invent containment/validation), mkdir only mode==write, candidate-first then first registry path with is_file short-circuit. Read mode has no write; write mode retains all former effects/errors. Do not change these path rules to package-root rules. Preserve future annotations, signatures/annotation strings, complete algorithms/literals, exact native errors and causes, guard/read/write/check order, unknowns, aliases, truthiness, borrowed values and fresh observations. Constructors are cold; distribution_root is explicit; actual workplace root is supplied per operation. No Main/Host imports, callbacks/providers/Any or ModuleType paths back to the monolith, duplicate existing path/parser/schema algorithms, new features/policies/caches/DI/framework or permission/lifecycle changes. No actual workplace writes; native characterization uses at most five synthetic cases with stub paths/I/O and extracted definitions. Parent alone performs bounded real scratch I/O, direct/copied Core imports and existing affected scripts. Own only declared files/artifacts/scratch; do not edit Main, docs, inventory or peer files. All peer APIs and full original algorithms are explicit in this brief/baseline; do not read a mutable peer file as a prepared input. Use exact PF selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed connected MCP is stale and must not be used/repaired. No Git mutations/remotes/infrastructure/nested agents/self lifecycle. Read original architecture, Python material and frozen concrete dependencies. Compile source without importing product modules. Produce Russian report.md and proof.json with schema described in brief, final raw hashes and exactly one final newline.

## semantics

Create project/platform_validation.py PlatformContractValidationService(distribution_root: Path).validate(workplace_root,data,platform,*,platform_resolution=None), complete original 141-line platform_contract_semantic_checks. Compose existing PlatformContractReader, PlatformContractPolicy(reader), PlatformContractResolver(root), ProjectPlatformSelectionService(root), ProjectPackageCatalogReader(root), ContextContractInputs and peer TemplateCatalogService(root).manifest. Existing API bodies and constructors are pinned. common.checks.check/Check, common.text.check_with_hint and common.values.list_value are canonical. Policy YAML receives explicit distribution_root. Preserve ALL ordered checks, repeated package index/template observations, optional/required semantics, exact messages/CLI hints, falsey platform_resolution fallback, inherited resources, stack/cycle/missing checks and short-circuits. Create common/policies.py containing exact standalone policy_entries and policy_id_matches (re.fullmatch), future annotations and borrowed dict semantics; these are shared by other unchanged Main operations. No class for these pure primitives. Prove full AST/literals/signature and ordering; include native invalid-regex error, borrowed dicts and recommendation/required/cycle observations in <=5 stubs. Preserve future annotations, signatures/annotation strings, complete algorithms/literals, exact native errors and causes, guard/read/write/check order, unknowns, aliases, truthiness, borrowed values and fresh observations. Constructors are cold; distribution_root is explicit; actual workplace root is supplied per operation. No Main/Host imports, callbacks/providers/Any or ModuleType paths back to the monolith, duplicate existing path/parser/schema algorithms, new features/policies/caches/DI/framework or permission/lifecycle changes. No actual workplace writes; native characterization uses at most five synthetic cases with stub paths/I/O and extracted definitions. Parent alone performs bounded real scratch I/O, direct/copied Core imports and existing affected scripts. Own only declared files/artifacts/scratch; do not edit Main, docs, inventory or peer files. All peer APIs and full original algorithms are explicit in this brief/baseline; do not read a mutable peer file as a prepared input. Use exact PF selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed connected MCP is stale and must not be used/repaired. No Git mutations/remotes/infrastructure/nested agents/self lifecycle. Read original architecture, Python material and frozen concrete dependencies. Compile source without importing product modules. Produce Russian report.md and proof.json with schema described in brief, final raw hashes and exactly one final newline.

## dependencies

Create project/requirements.py PlatformDependencyPreflightService(distribution_root: Path).check(workplace_root,required_packages,required_templates,required_tools,required_mcp) and registry_ids(workplace_root,registry_name,collection_key). Compose existing ProjectPackageCatalogReader(root), peer TemplateCatalogService(root), ContextContractInputs/YamlDocumentReader and common.values.registry_ids. Peer APIs are fully declared in brief and baseline; no lazy imports or Main adapter. Preserve package manifest list truthiness, template is None check, unconditional tools then MCP registry reads after loops even empty requirements, duplicate missing IDs/list order and exact SystemExit joined message. registry_ids must read literal workplace_root/registries/name, retaining canonical set semantics and YAML-error behavior. No global root or document cache. Characterize entire trace and native failures with <=5 stubs. Preserve future annotations, signatures/annotation strings, complete algorithms/literals, exact native errors and causes, guard/read/write/check order, unknowns, aliases, truthiness, borrowed values and fresh observations. Constructors are cold; distribution_root is explicit; actual workplace root is supplied per operation. No Main/Host imports, callbacks/providers/Any or ModuleType paths back to the monolith, duplicate existing path/parser/schema algorithms, new features/policies/caches/DI/framework or permission/lifecycle changes. No actual workplace writes; native characterization uses at most five synthetic cases with stub paths/I/O and extracted definitions. Parent alone performs bounded real scratch I/O, direct/copied Core imports and existing affected scripts. Own only declared files/artifacts/scratch; do not edit Main, docs, inventory or peer files. All peer APIs and full original algorithms are explicit in this brief/baseline; do not read a mutable peer file as a prepared input. Use exact PF selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py; installed connected MCP is stale and must not be used/repaired. No Git mutations/remotes/infrastructure/nested agents/self lifecycle. Read original architecture, Python material and frozen concrete dependencies. Compile source without importing product modules. Produce Russian report.md and proof.json with schema described in brief, final raw hashes and exactly one final newline.

## Native proof schema and bounded assurance

Each proof.json must have status="passed", algorithms mapping EVERY assigned original function name to {full_ast_equal:true, signature_equal:true, annotations_equal:true}, products mapping every owned product path directly to its raw SHA256 hex, prior_owners mapping each unchanged frozen dependency to {raw_equal:true,ast_equal:true}, and synthetic_cases list with {id,status:"passed"}. Keep full normalized AST/signature evidence or hashes and exact allowed renamings alongside these flags. Existing common.values has separate prior_module_preservation {raw_prefix_equal:true,full_prior_ast_equal:true,only_appended:"upsert_resource"}. Complete proof compares every literal/node, not only function shape/count; preserve full observations. At most five meaningful stub scenarios per worker, no repeat after success.

Primary removes all nine original definitions, imports shared functions and builds four cold owners; migrates all actual callers, no compatibility aliases. Parent preflights edits and proves full 730 retained-definition Main AST, exact shared funcs/prior values.py and readonly owners. Parent alone runs real scratch registry writes/refusals/injected replace failure, actual template read/write fallbacks and platform/default/composition cases, direct/copied Core without transport. Use a small set of affected existing scripts (registry corruption safety, platform include levels, platform layout/selection and docs). No permanent suite, full Runtime/recovery/release/archive/install/connected-host or ZIP checking. Native success means report and proof actually read, not just exit0.

Review after implementation/QA on exact final product hashes. Commit selected source/evidence only; push same commit parallel to origin/dev and gitverse/dev, existing GITVERSE_TOKEN with credential helper/tracing disabled, full SHA readback. Preserve unrelated state. Close exact Works/root doctor; reread all nine architecture docs and fresh context before next bounded scope. Stop new admission at device 09:00 and finish in-flight work.
