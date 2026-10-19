# Resource records, package/index diagnostics and worker assignment prompt

Baseline `5bb90b6fe072c3c57f8ec5c27700f3c87025ea82`: thirteenth scope delivered to both dev heads; six exact Works terminal/root doctor PASS. All nine original architecture docs fully reread after delivery; source context fresh/ready/continue and source/index clean. Four disjoint native shell workers, then independent clean-context reviewer. High effort for all four: complex normalization/read traces and six-module consumer closure. No nested agents or extra coordinators.

Use existing SOURCE CLI and exact prepared Work selectors for PF reads; no installed MCP use/repair/infrastructure. PF Python excerpts/provenance and full concrete dependencies are explicit inputs. External release contract remains 1.2.0; no new features or MCP resources. Preserve D01/D02/D03/D06/D07/D09/D11 and applicable R01-R12, including unknowns, order, live reads and source/evidence layers.

Ownership:
```json
{
  "records": [
    "src/processforge_core/resources/records.py"
  ],
  "doctor": [
    "src/processforge_core/resources/package_checks.py"
  ],
  "indexes": [
    "src/processforge_core/resources/index_checks.py",
    "src/processforge_core/common/paths.py"
  ],
  "prompts": [
    "src/processforge_core/work/worker_assignment.py",
    "tools/pf_runtime/host.py",
    "tools/smoke_continuation_work.py",
    "tools/smoke_expected_report_containment.py",
    "tools/smoke_prepared_execution_context.py",
    "tools/smoke_prepared_execution_recovery.py",
    "tools/smoke_process_run_task_batch.py"
  ],
  "review": []
}
```

Exact service APIs:
```json
{
  "records": {
    "class": "ResourceRecordService",
    "module": "resources/records.py",
    "methods": {
      "default_load_policy": "load_policy",
      "default_index_policy": "index_policy",
      "path_ref_for_known_root": "known_root",
      "public_resource_path_ref": "public_ref",
      "normalize_resource_record": "normalize"
    },
    "constructor": "none"
  },
  "doctor": {
    "class": "KnowledgePackageValidationService",
    "module": "resources/package_checks.py",
    "methods": {
      "knowledge_package_doctor_checks": "doctor"
    },
    "constructor": "distribution_root"
  },
  "indexes": {
    "class": "KnowledgeResourceIndexService",
    "module": "resources/index_checks.py",
    "methods": {
      "resource_index_path_for_package": "index_path",
      "resource_path_ref_missing": "path_ref_missing",
      "project_knowledge_resource_index_checks": "project_checks"
    },
    "constructor": "distribution_root"
  },
  "prompts": {
    "class": "WorkerAssignmentService",
    "module": "work/worker_assignment.py",
    "methods": {
      "load_task": "load",
      "render_worker_launch_prompt": "render_prompt"
    },
    "constructor": "none"
  }
}
```

records/prompts constructors take NO arguments; doctor/indexes take distribution_root: Path. No constructor I/O. Each operation supplies its actual project/workplace root. HEAVY_RESOURCE_KINDS moves exactly to resources.records.HEAVY_RESOURCE_KINDS; path_is_relative_to moves exactly to existing common.paths. Main imports those canonical values/functions and builds four cold services. No internal compatibility wrappers. All twelve full originals, the exact constant and dependency references are pinned in baseline-functions.json.

Canonical methods were verified before admission: WorkspacePathReferenceReader(...).workplace_path_resolution/normalize_path_string/path_string_is_absolute/validate_resource_id/contained_resource_path; ResourceSnapshotRules().versioning_policy; ProjectPackageCatalogReader(root).load_manifest/candidates/index/dependencies; UpdateDocumentReader(root).doctor_yaml; PlatformDependencyPreflightService(root).registry_ids; YamlDocumentReader.read/load; ProjectMetadataReader(project_root).flow_root; WorkPaths.assignment_document/worker_run. Reuse these owners. WorkMetadataReadPass is a projected per-operation reader and is deliberately not substituted for strict full load_task.

Native proof schema: status="passed"; algorithms mapping EVERY assigned original function to {full_ast_equal:true,signature_equal:true,annotations_equal:true}; products maps EVERY owned product path directly to raw SHA256 hex; prior_owners records unchanged frozen dependencies {raw_equal:true,ast_equal:true}; synthetic_cases list {id,status:"passed"}, at most five. Retain complete AST/signature/trace observations or hashes and exact limited renamings. records has constants_exact=true; indexes has prior_module_preservation {raw_prefix_equal:true,full_prior_ast_equal:true,only_appended:"path_is_relative_to"}; prompts has consumer_preservation for EACH existing consumer with full_ast_equal=true,raw_only_declared_changes=true and substitutions count. Reports include no private absolute paths.

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

Frozen concrete dependencies:
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__checks.py.txt`
- `src/processforge_core/common/text.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__text.py.txt`
- `src/processforge_core/common/privacy.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__privacy.py.txt`
- `src/processforge_core/common/policies.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__policies.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/values.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__values.py.txt`
- `src/processforge_core/common/ids.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__ids.py.txt`
- `src/processforge_core/common/paths.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__common__paths.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__documents__reader.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__work__context_documents.py.txt`
- `src/processforge_core/work/paths.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__work__paths.py.txt`
- `src/processforge_core/resources/snapshot.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__resources__snapshot.py.txt`
- `src/processforge_core/resources/project_packages.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__resources__project_packages.py.txt`
- `src/processforge_core/project/metadata.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__project__metadata.py.txt`
- `src/processforge_core/project/resource_snapshot.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__project__resource_snapshot.py.txt`
- `src/processforge_core/project/requirements.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__project__requirements.py.txt`
- `src/processforge_core/maintenance/documents.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__maintenance__documents.py.txt`
- `src/processforge_core/maintenance/schema_checks.py` => `.pf/artifacts/pf121-oop-core-resources-20261018/primary/inputs/processforge_core__maintenance__schema_checks.py.txt`

The prompts worker additionally receives full immutable consumer before-images; other workers do not need those bodies.

## records

Create resources/records.py ResourceRecordService() with load_policy(kind,requested=None), index_policy(kind,requested=None), known_root(workplace_root,raw_path), public_ref(resource_id,raw_path,source_url=None,workplace_root=None), normalize(resource,package_id,workplace_root=None,*,register_private_path=False), matching all five originals. Move exact HEAVY_RESOURCE_KINDS set from baseline constants into this module; other new owners import it. Reuse canonical safe_id, ContextContractInputs.path_string_is_absolute and PATH_CONSTANT_PATTERN, WorkspacePathReferenceReader with actual workplace_root for workplace_path_resolution/normalize_path_string, and existing ResourceSnapshotRules().versioning_policy(record) per original call. No copied path resolver or snapshot algorithms. Preserve registered-root list order/first match/case-sensitive prefix, repeated registry/path observations, external URL precedence, private path hiding, borrowed nested fields and shallow dict copy, unknown path_ref behavior and exact default maps. register_private_path currently has NO write effect: keep the argument ignored as before. Constructor takes no root and performs no I/O. Extra request-local concrete reader assembly is allowed only cold with original call order; prove every other node/literal. Own all five methods and the exact constant. Preserve complete algorithms/literals, future annotations and exact signature/annotation strings, unknown fields, borrowed values, fresh observations, native errors/causes and guard/read/check order. Constructors are cold; roots are operation-local and documents never cached. No Main/Host imports or backwards callback/provider/Any facades, new functionality/policies/DI/framework/permission/lifecycle changes, duplicate existing parsing/path/snapshot/schema rules, timestamp changes, actual workplace mutation, network/infrastructure/Git mutations or nested agents. Use exact prepared Work selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py when necessary; installed MCP is stale and is not used/repaired. Read architecture, PF Python excerpts and frozen concrete dependencies. Peer APIs are declared fully here and algorithms pinned in baseline; do not pin/read mutable peer sources as inputs. Compile without importing product modules; at most five synthetic cases from extracted definitions and stubs, no successful repeats. Parent alone does assembled imports, real scratch fixtures and affected existing scripts. Own declared paths only; leave Main/docs/inventory and peer files. Produce Russian report.md and proof.json in the exact brief schema and final raw product hashes; exactly one final newline.

## doctor

Create resources/package_checks.py KnowledgePackageValidationService(distribution_root: Path).doctor(workplace_root,package_id,package_root_id=None), full 101-line original. Compose actual ProjectPackageCatalogReader(root), UpdateDocumentReader(root) from maintenance.documents, ContextContractInputs, peer ResourceRecordService(), peer KnowledgeResourceIndexService(root), canonical Check/check/check_with_hint/privacy and policy primitives. Reuse resources.records.HEAVY_RESOURCE_KINDS. Preserve initial manifest load plus separate doctor_yaml reread, warning levels/order, schema refusal return, normalization/resource path refs, heavy resource warnings, index checks, public path text check, navigation, dependency index/policy ordering and repeated observations. New index owner API is index_path(manifest_path,workplace_root,package_id), path_ref_missing(workplace_root,resource), project_checks(project_root,distribution_root,workplace_manifest). Do not collapse reads, infer validation or add registration. Preserve complete algorithms/literals, future annotations and exact signature/annotation strings, unknown fields, borrowed values, fresh observations, native errors/causes and guard/read/check order. Constructors are cold; roots are operation-local and documents never cached. No Main/Host imports or backwards callback/provider/Any facades, new functionality/policies/DI/framework/permission/lifecycle changes, duplicate existing parsing/path/snapshot/schema rules, timestamp changes, actual workplace mutation, network/infrastructure/Git mutations or nested agents. Use exact prepared Work selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py when necessary; installed MCP is stale and is not used/repaired. Read architecture, PF Python excerpts and frozen concrete dependencies. Peer APIs are declared fully here and algorithms pinned in baseline; do not pin/read mutable peer sources as inputs. Compile without importing product modules; at most five synthetic cases from extracted definitions and stubs, no successful repeats. Parent alone does assembled imports, real scratch fixtures and affected existing scripts. Own declared paths only; leave Main/docs/inventory and peer files. Produce Russian report.md and proof.json in the exact brief schema and final raw product hashes; exactly one final newline.

## indexes

Create resources/index_checks.py KnowledgeResourceIndexService(distribution_root: Path) with index_path(manifest_path,workplace_root,package_id), path_ref_missing(workplace_root,resource), project_checks(project_root,distribution_root,workplace_manifest), matching the three full originals. Compose ProjectPackageCatalogReader(root), ContextContractInputs/YamlDocumentReader, peer ResourceRecordService() and existing PlatformDependencyPreflightService(root).registry_ids. For index path validation reuse actual WorkspacePathReferenceReader with the operation workplace root: validate_resource_id and contained_resource_path are existing canonical implementations. Retain package.yaml early return BEFORE validation, flat fallback containment, exact six registry mappings/external exemptions and package-only path_ref semantics. project_checks keeps all candidate/read/error/empty skips, root selection/relative containment, optional local indexes, unknown/nonobject resource checks and heavy warnings in original order. Append exact standalone path_is_relative_to to existing common.paths with entire prior AST/raw bytes prefix/imports intact; it resolves BOTH inputs and catches ONLY ValueError. Other Main callers import this same canonical function. Preserve signatures including distribution_root operation argument distinct from service distribution root. Reuse peer HEAVY_RESOURCE_KINDS constant. Preserve complete algorithms/literals, future annotations and exact signature/annotation strings, unknown fields, borrowed values, fresh observations, native errors/causes and guard/read/check order. Constructors are cold; roots are operation-local and documents never cached. No Main/Host imports or backwards callback/provider/Any facades, new functionality/policies/DI/framework/permission/lifecycle changes, duplicate existing parsing/path/snapshot/schema rules, timestamp changes, actual workplace mutation, network/infrastructure/Git mutations or nested agents. Use exact prepared Work selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py when necessary; installed MCP is stale and is not used/repaired. Read architecture, PF Python excerpts and frozen concrete dependencies. Peer APIs are declared fully here and algorithms pinned in baseline; do not pin/read mutable peer sources as inputs. Compile without importing product modules; at most five synthetic cases from extracted definitions and stubs, no successful repeats. Parent alone does assembled imports, real scratch fixtures and affected existing scripts. Own declared paths only; leave Main/docs/inventory and peer files. Produce Russian report.md and proof.json in the exact brief schema and final raw product hashes; exactly one final newline.

## prompts

Create work/worker_assignment.py WorkerAssignmentService() with load(project_root,task_id) and render_prompt(project_root,task_id,*,prepared_input=None). Compose concrete WorkPaths(), ContextContractInputs(), YamlDocumentReader(_parse_simple_yaml) or inputs.documents, and ProjectMetadataReader(project_root).flow_root() on the actual operation. load preserves original assignment path safe_id behavior, explicit missing-file guard and EXACT SystemExit text, then strict documents.read rather than soft load or metadata projection. render_prompt is the entire 92-line original, with safe_id/load order, all English literals/sections/blank lines, workspace access normalization/counts, prepared_input falsey behavior, required outputs/report/subagent policy fields, path formatting and final newline. No actual preparation/launch/policy changes. Also own the six explicit consumer files in ownership: exactly eleven core.load_task calls (two host, one continuation smoke, one containment smoke, two prepared context, three prepared recovery, two run-task batch) become calls to concrete WorkerAssignmentService().load through one cold module instance/import per file. Add imports through the established sys.path/import bootstrap AFTER it is available; inspect frozen full consumer before-images. Do not edit any assertion, test fixture, class, signature, JSON/worker/guard logic or other source node. Native proof must show full AST AND raw bytes differ only in declared import/instance/call-target edits for EACH consumer. No actual imports/runs by native; parent runs affected scripts. Helpers named load_task on fakes or unrelated readers remain distinct. Preserve complete algorithms/literals, future annotations and exact signature/annotation strings, unknown fields, borrowed values, fresh observations, native errors/causes and guard/read/check order. Constructors are cold; roots are operation-local and documents never cached. No Main/Host imports or backwards callback/provider/Any facades, new functionality/policies/DI/framework/permission/lifecycle changes, duplicate existing parsing/path/snapshot/schema rules, timestamp changes, actual workplace mutation, network/infrastructure/Git mutations or nested agents. Use exact prepared Work selectors and existing SOURCE CLI python -B -X utf8 tools/processforge.py when necessary; installed MCP is stale and is not used/repaired. Read architecture, PF Python excerpts and frozen concrete dependencies. Peer APIs are declared fully here and algorithms pinned in baseline; do not pin/read mutable peer sources as inputs. Compile without importing product modules; at most five synthetic cases from extracted definitions and stubs, no successful repeats. Parent alone does assembled imports, real scratch fixtures and affected existing scripts. Own declared paths only; leave Main/docs/inventory and peer files. Produce Russian report.md and proof.json in the exact brief schema and final raw product hashes; exactly one final newline.

## Primary and delivery

Remove twelve old function definitions and the heavy-kind constant; all Main operations call concrete owners. All six actual assignment consumers migrate in the same scope; unrelated callback paths remain explicit residual migration. Preflight every primary edit before writes. Native full algorithms/annotations/readonly owners are checked once. Parent verifies complete 718 remaining-definition Main AST, all six consumer AST/raw boundaries, exact common.paths prior module and shared constant, actual direct/copied Core, small real scratch package/index/record/prompt cases and all changed existing scripts. Retain successes; no permanent tests or full Runtime/recovery/release/archive/install/connected-host/ZIP qualification. Existing prepared recovery smoke is affected by a declared strict read-target change and is bounded source assurance, not Runtime acceptance. Independent review after implementation/QA, exact path/raw hash reference for Main without redundant whole-file prompt capture.

One accepted source commit, parallel pushes origin/dev and gitverse/dev with GITVERSE_TOKEN only, helper/tracing disabled and full SHA readback; preserve foreign state. Complete six exact Works/root doctor, fully reread original architecture and fresh context before next scope. No new admission after device 09:00; finish in-flight work and report.
