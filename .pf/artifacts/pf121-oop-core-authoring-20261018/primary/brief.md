# Authoring models/read inputs, process presentation and candidate reading

Baseline `777d3b145f12a27ec317f2628795ca89f3189b8f`: fourteenth slice delivered identically to both dev heads, six current Works terminal/root doctor PASS, two historical cancelled implementation attempts retained. All nine original architecture docs fully reread afterward; current source context fresh/ready/continue and product/index clean. Sequential 1-1-4 native shell mode; models/inputs/process/review high effort, updates medium. No nested agents.

Use SOURCE CLI exact selectors only, not stale installed MCP or infrastructure. PF Python excerpts/provenance and frozen concrete owners are explicit required sources. Canonical APIs verified before admission. Preserve external 1.2.0 contracts, D01/D02/D03/D06/D07/D09/D11 and applicable R01-R12. No new features/MCP resources/permissions/DI/framework.

Ownership:
```json
{
  "models": [
    "src/processforge_core/authoring/__init__.py",
    "src/processforge_core/authoring/plans.py",
    "tools/smoke_authoring_crash_recovery.py",
    "tools/smoke_remediation_transactional_authoring.py"
  ],
  "inputs": [
    "src/processforge_core/authoring/inputs.py",
    "src/processforge_core/common/digests.py"
  ],
  "process": [
    "src/processforge_core/process_catalog/examples.py",
    "src/processforge_core/presentation/process_parity.py",
    "src/processforge_core/common/status.py"
  ],
  "updates": [
    "src/processforge_core/maintenance/candidate_read.py"
  ],
  "review": []
}
```

APIs:
```json
{
  "models": {
    "class": "AuthoringPlanRenderer",
    "module": "authoring/plans.py",
    "constructor": "none",
    "instance": "_authoring_plan_renderer",
    "methods": {
      "render_authoring_plan": "render"
    }
  },
  "inputs": {
    "class": "AuthoringInputService",
    "module": "authoring/inputs.py",
    "constructor": "none",
    "instance": "_authoring_input_service",
    "methods": {
      "authoring_mode": "mode",
      "authoring_transaction_root": "transaction_root",
      "authoring_journal_path": "journal_path",
      "incomplete_authoring_journals": "incomplete_journals",
      "validate_authoring_parent_types": "parent_types",
      "authoring_parent_chain": "parent_chain"
    }
  },
  "process": {
    "class": "ProcessAuthoringExampleBuilder",
    "module": "process_catalog/examples.py",
    "constructor": "none",
    "instance": "_process_authoring_example_builder",
    "methods": {
      "build_process_authoring_example_documents": "build"
    }
  },
  "updates": {
    "class": "UpdateCandidateReader",
    "module": "maintenance/candidate_read.py",
    "constructor": "distribution_root",
    "instance": "_update_candidate_reader",
    "methods": {
      "read_update_candidates": "read",
      "find_update_candidate": "find"
    }
  }
}
```

Canonical standalone/model owners:
```json
{
  "AuthoringWrite": "authoring.plans.AuthoringWrite",
  "AuthoringEffect": "authoring.plans.AuthoringEffect",
  "AuthoringPlan": "authoring.plans.AuthoringPlan",
  "process_yaml_content": "process_catalog.examples.process_yaml_content",
  "aggregate_status": "common.status.aggregate_status"
}
```

Existing Main object method bindings (reuse these exact current instances):
```json
{
  "authoring_hash_bytes": "_file_digests.sha256_bytes",
  "authoring_file_hash": "_file_digests.sha256_optional_file",
  "render_parity_index": "_process_parity_renderer.index"
}
```

The three dataclasses move as exact inert data carriers. Callback execution, preflight callbacks, AUTHORING_FAILURE_INJECTOR, staging/publication/rollback remain UNMIGRATED in Main; selected Core never invokes those callbacks. Raw-byte guarded authoring hash differs from existing streaming FileDigestReader.sha256_file I/O, so append the exact two original algorithms to that same owner and retain streaming method untouched. Existing maintenance.update.now_utc has identical full AST and is reused, without a new clock/callback. Constructors are cold; no authoring mutation in this slice.

All selected identifiers were scanned including processforge/pf/core attributes, direct imports and exact strings; only the two assigned consumer scripts matched. They bootstrap Main locally, so use operation-local canonical imports after bootstrap, with assertions/fixtures/failure-injection phases exact. Peer models/inputs APIs and full originals are explicitly pinned, not live peer source captures.

Native proof schema: status="passed"; algorithms maps EVERY assigned original definition (including classes) to full_ast_equal/signature_equal/annotations_equal=true; products maps every owned file directly to raw SHA256 hex; prior_owners for unchanged frozen dependencies {raw_equal:true,ast_equal:true}; synthetic_cases <=5 {id,status:"passed"}. Retain full normalized AST/data/signature/trace or hashes and exact allowed substitutions. models also model_contracts_exact=true and consumer_preservation for BOTH scripts {full_ast_equal:true,raw_only_declared_changes:true,assertions_unchanged:true,fixtures_unchanged:true,no_eager_core_imports:true}. inputs prior_module_preservation checks old FileDigestReader AST/raw prefix/fields/signatures intact after removing two new methods. process prior_module_preservation checks all prior ProcessParityRenderer nodes/raw except exactly canonical import insertion/new method. No successful native repeats.

Architecture:
- `.pf/artifacts/original-architecture-alignment-20261010/migration-contract.md`
- `.pf/artifacts/progressive-oop-boundary-20261010/decision.md`
- `.pf/artifacts/oop-refactor-clarification-20261005/clarification.md`
- `.pf/artifacts/pf-framework-architecture-20261005/adr.md`
- `.pf/artifacts/pf-framework-architecture-20261005/domain.md`
- `.pf/artifacts/pf-framework-architecture-20261005/direction.md`
- `.pf/artifacts/python-framework-20261005/oop-02.md`
- `.pf/artifacts/python-framework-20261005/oop-03.md`
- `.pf/artifacts/python-framework-20261005/oop-05.md`

Frozen concrete sources:
- `src/processforge_core/common/checks.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__checks.py.txt`
- `src/processforge_core/common/text.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__text.py.txt`
- `src/processforge_core/common/paths.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__paths.py.txt`
- `src/processforge_core/common/ids.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__ids.py.txt`
- `src/processforge_core/common/yaml_io.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__yaml_io.py.txt`
- `src/processforge_core/common/yaml_dump.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__yaml_dump.py.txt`
- `src/processforge_core/common/digests.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__common__digests.py.txt`
- `src/processforge_core/documents/reader.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__documents__reader.py.txt`
- `src/processforge_core/work/context_documents.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__work__context_documents.py.txt`
- `src/processforge_core/presentation/process_parity.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__presentation__process_parity.py.txt`
- `src/processforge_core/maintenance/documents.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__maintenance__documents.py.txt`
- `src/processforge_core/maintenance/update.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/src__processforge_core__maintenance__update.py.txt`
- `tools/smoke_authoring_crash_recovery.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/tools__smoke_authoring_crash_recovery.py.txt`
- `tools/smoke_remediation_transactional_authoring.py` => `.pf/artifacts/pf121-oop-core-authoring-20261018/primary/inputs/tools__smoke_remediation_transactional_authoring.py.txt`

## models

Create minimal empty authoring/__init__.py and authoring/plans.py containing EXACT dataclasses AuthoringWrite, AuthoringEffect and AuthoringPlan, including decorators/defaults/field(default_factory=dict), all field order and Any callback data annotations. Preserve dataclass flags, constructor positional/default behavior, mutation/equality/repr/asdict and per-instance payload identity; no new methods or fields. Add stateless AuthoringPlanRenderer().render(plan,root) with complete original render_authoring_plan: same stdout print sequence, sorted rows, seven data fields/conditions, native errors and no callback execution. Core model module location is the declared relocation; annotation strings/qualnames and other dataclass behavior remain original. Also own the TWO existing consumer scripts: replace processforge.AuthoringPlan/AuthoringWrite/AuthoringEffect with direct canonical class imports, and processforge.authoring_journal_path with a concrete peer AuthoringInputService().journal_path. Peer inputs API takes no constructor args and exact plan path algorithms are pinned. These scripts initially import only tools and bootstrap processforge LOCALLY/in main; canonical imports/instances must therefore be LOCAL to the existing operation functions after actual caller bootstrap, never eager at module scope. No sys.path/bootstrap change. Preserve all assertions, fixture values, failure-injection callbacks/phase matrices and other calls. Full AST/raw proof for each consumer permits only declared imports/cold instances/targets; no extra changes. Preserve every AST node/literal beyond exact owner/name/self substitutions, future/signature/annotation strings, data/identity/aliases, guard/read/check/print order, native errors and causes, unknowns and fresh observations. Constructors are cold, roots passed per operation, no retained parsed documents. No Main/Host imports or callback/provider/Any facades back to Main, duplicate complex path/parser/digest behavior, new features/policies/permissions/cache/DI/framework, lifecycle/atomicity/recovery changes, workplace writes, network, Git/remotes/infrastructure/nested agents/self transitions. Existing callbacks carried as model DATA remain inert in the moved scope; never call validation/effect/failure callbacks from new code. Preflight/transactions/staging/commit/rollback/failure injection remain explicitly in Main. Use exact SOURCE CLI selectors if needed, never stale installed MCP. Read required architecture/PF Python/frozen inputs. Compile without importing product modules; at most five meaningful stub/model scenarios, no repeats after success. Parent alone performs real scratch/default/copy imports and affected scripts. Own assigned products/artifacts/scratch only, not Main/docs/inventory or peer files. End files with exactly one newline. Russian report plus proof.json with final raw hashes and full AST/signature/data/prior-owner evidence.

## inputs

Create authoring/inputs.py AuthoringInputService() methods mode(args), transaction_root(plan), journal_path(plan), incomplete_journals(runtime_root), parent_types(destination), parent_chain(path), matching SIX originals exactly. Compose existing ContextContractInputs/YamlDocumentReader.load for soft journal parsing; malformed/nonterminal journals remain blocking, sorted */journal.yaml and exact terminal set preserved. Keep duplicate exists/is_dir observations, missing-chain list construction and reverse order, exact SystemExit and bool(getattr) mode behavior. Import peer AuthoringPlan for original annotation string; no callback invocation. Also append TWO exact methods to EXISTING frozen FileDigestReader in common/digests.py: sha256_bytes(content:bytes)->str from authoring_hash_bytes, sha256_optional_file(path:Path)->str|None from authoring_file_hash, with only method name/self changes. Existing streaming sha256_file MUST remain unchanged; it has different I/O observations from the guarded read_bytes helper. Do not implement optional-file helper using streaming method. Preserve entire prior module AST/raw prefix and dataclass constructor/fields, no imports needed beyond its existing hashlib/Path. Main reuses existing _file_digests instance for both new methods; no wrappers or extra digest instance. Preserve every AST node/literal beyond exact owner/name/self substitutions, future/signature/annotation strings, data/identity/aliases, guard/read/check/print order, native errors and causes, unknowns and fresh observations. Constructors are cold, roots passed per operation, no retained parsed documents. No Main/Host imports or callback/provider/Any facades back to Main, duplicate complex path/parser/digest behavior, new features/policies/permissions/cache/DI/framework, lifecycle/atomicity/recovery changes, workplace writes, network, Git/remotes/infrastructure/nested agents/self transitions. Existing callbacks carried as model DATA remain inert in the moved scope; never call validation/effect/failure callbacks from new code. Preflight/transactions/staging/commit/rollback/failure injection remain explicitly in Main. Use exact SOURCE CLI selectors if needed, never stale installed MCP. Read required architecture/PF Python/frozen inputs. Compile without importing product modules; at most five meaningful stub/model scenarios, no repeats after success. Parent alone performs real scratch/default/copy imports and affected scripts. Own assigned products/artifacts/scratch only, not Main/docs/inventory or peer files. End files with exactly one newline. Russian report plus proof.json with final raw hashes and full AST/signature/data/prior-owner evidence.

## process

Create process_catalog/examples.py with exact standalone process_yaml_content(value), using canonical common.text.ensure_trailing_newline/common.yaml_dump.dump_yaml, and ProcessAuthoringExampleBuilder().build(project_root,process,answers,review_text) containing the full original seven path/bytes result construction. Reuse actual common.ids.title_from_id. Preserve literal Markdown/f-string/newline/YAML bytes, output path/list/key order, truthiness/native failures and no disk writes. Add exact render_parity_index as index(rows,title) to EXISTING presentation/process_parity.py ProcessParityRenderer, with name/self changes and canonical aggregate_status import only. Preserve all prior methods, complete prior AST and raw bytes except that necessary import insertion and appended method; do not rebuild or move that existing class. Create common/status.py exact standalone aggregate_status (shared by other unchanged Main operations), future annotations and exact falsey filtering/FAIL/WARN/all-SKIP/otherwise PASS behavior, no class for a pure primitive. Parent reuses existing Main _process_parity_renderer instance; no new renderer composition for this existing owner. Preserve every AST node/literal beyond exact owner/name/self substitutions, future/signature/annotation strings, data/identity/aliases, guard/read/check/print order, native errors and causes, unknowns and fresh observations. Constructors are cold, roots passed per operation, no retained parsed documents. No Main/Host imports or callback/provider/Any facades back to Main, duplicate complex path/parser/digest behavior, new features/policies/permissions/cache/DI/framework, lifecycle/atomicity/recovery changes, workplace writes, network, Git/remotes/infrastructure/nested agents/self transitions. Existing callbacks carried as model DATA remain inert in the moved scope; never call validation/effect/failure callbacks from new code. Preflight/transactions/staging/commit/rollback/failure injection remain explicitly in Main. Use exact SOURCE CLI selectors if needed, never stale installed MCP. Read required architecture/PF Python/frozen inputs. Compile without importing product modules; at most five meaningful stub/model scenarios, no repeats after success. Parent alone performs real scratch/default/copy imports and affected scripts. Own assigned products/artifacts/scratch only, not Main/docs/inventory or peer files. End files with exactly one newline. Russian report plus proof.json with final raw hashes and full AST/signature/data/prior-owner evidence.

## updates

Create maintenance/candidate_read.py UpdateCandidateReader(distribution_root:Path) with read(workplace_root) and find(workplace_root,candidate_id), entire originals. Compose actual UpdateDocumentReader(root).candidates_path (runtime/update/candidates.json; no mkdir) and canonical maintenance.update.now_utc. That EXISTING clock algorithm was verified identical to Main now_utc, so reuse it without copying a clock or injecting a Main callback. Preserve repeated default dictionary literals, fallback only for missing/non-dict/JSONDecodeError, no OSError/UnicodeDecodeError catch, one fresh UTC call per fallback and zero for valid dict, first candidate matching raw ID equality, borrowed return item and fresh file reads. No constructor I/O/clock or hidden workplace root, no new behavior. Parent freezes canonical clock ONLY in characterization, not product API. Preserve every AST node/literal beyond exact owner/name/self substitutions, future/signature/annotation strings, data/identity/aliases, guard/read/check/print order, native errors and causes, unknowns and fresh observations. Constructors are cold, roots passed per operation, no retained parsed documents. No Main/Host imports or callback/provider/Any facades back to Main, duplicate complex path/parser/digest behavior, new features/policies/permissions/cache/DI/framework, lifecycle/atomicity/recovery changes, workplace writes, network, Git/remotes/infrastructure/nested agents/self transitions. Existing callbacks carried as model DATA remain inert in the moved scope; never call validation/effect/failure callbacks from new code. Preflight/transactions/staging/commit/rollback/failure injection remain explicitly in Main. Use exact SOURCE CLI selectors if needed, never stale installed MCP. Read required architecture/PF Python/frozen inputs. Compile without importing product modules; at most five meaningful stub/model scenarios, no repeats after success. Parent alone performs real scratch/default/copy imports and affected scripts. Own assigned products/artifacts/scratch only, not Main/docs/inventory or peer files. End files with exactly one newline. Russian report plus proof.json with final raw hashes and full AST/signature/data/prior-owner evidence.

## Primary assurance/delivery

Remove 18 top-level definitions (3 classes/15 functions), expecting 700 retained Main definitions. For classes remove decorators together. Import exact canonical models/standalone functions and compose only three new cold objects plus candidate reader; REUSE _file_digests and _process_parity_renderer. Preflight primary edits before writes; update EN/RU ownership/inventory only. Native proves full original algorithms/models/consumer/prior-owner boundary once; primary verifies complete Main AST, real scratch paths/journals/digest/native refusals, model fields/aliases/stdout/bytes, actual JSON candidate default/read/error behavior with test-only frozen canonical clock, default/copied Core and affected existing scripts. No permanent tests or broad release/archive/install/Runtime/connected-host/ZIP qualification. Preserve successful receipts and all assertions. Independent clean-context review at final raw hashes; Main declared exact reference/full AST privately, not whole-file prompt capture. One selected commit parallel to both dev remotes, GitVerse existing token with helper/tracing disabled, full SHA readback; preserve foreign state. Close exact Works/root doctor, fully reread all original architecture docs and context before next scope. No new admission after device 09:00; finish current work and report.
