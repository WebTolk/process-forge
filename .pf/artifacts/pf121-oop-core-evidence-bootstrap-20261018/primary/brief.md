# Journal storage, parameter sources, report projections and project inputs

Baseline ac58a1a9f1e91c9fe742f69d644833634a38520e: slice16 dual dev delivered, six Works terminal/root doctor PASS; all nine original architecture inputs fully reread, source context fresh/ready/continue, product/index clean. Sequential 1-1-4 native shell mode, journal/parameters/project/review high and reports medium effort. PF Python material/provenance and exact full frozen concrete inputs required. Source-only 1.2.0 behavior preserved.

Seventeen algorithms and two exact constants move into four concrete responsibilities, seven worker products plus four primary products (eleven total). Three actual consumer files belong to the matching worker. Explicit consumer AST closure is part of acceptance; no Main callback for migrated functions. Existing coordination methods/JSON strings with similar names have different contracts and stay unchanged. No features/MCP resources/permissions/DI/framework/infra. Applicable D01/D02/D03/D06/D07/D09/D11 and R01-R12 preserved.

Ownership:
```json
{
  "journal": [
    "src/processforge_core/authoring/journals.py"
  ],
  "parameters": [
    "src/processforge_core/configuration/parameter_sources.py",
    "src/processforge_core/work/context.py"
  ],
  "reports": [
    "src/processforge_core/project/report_read.py",
    "tools/smoke_remediation_aggregate_gates.py"
  ],
  "project": [
    "src/processforge_core/project/initialization_inputs.py",
    "src/processforge_core/project/initialization.py"
  ],
  "review": []
}
```
APIs:
```json
{
  "journal": {
    "class": "AuthoringJournalStore",
    "module": "authoring/journals.py",
    "constructor": "none",
    "instance": "_authoring_journal_store",
    "methods": {
      "write_authoring_journal_data": "write_data",
      "write_authoring_journal": "write"
    }
  },
  "parameters": {
    "class": "ParameterSourceService",
    "module": "configuration/parameter_sources.py",
    "constructor": "none",
    "instance": "_parameter_source_service",
    "methods": {
      "parameter_source_record": "record",
      "workplace_parameter_paths": "workplace_paths",
      "add_parameter_source": "add",
      "process_parameters_from_path": "process_parameters",
      "requirements_fingerprints": "requirements_fingerprints"
    }
  },
  "reports": {
    "class": "ReportProjectionReader",
    "module": "project/report_read.py",
    "constructor": "none",
    "instance": "_report_projection_reader",
    "methods": {
      "report_section_items": "section_items",
      "report_section_has_items": "section_has_items",
      "report_has_missing_required_capabilities": "has_missing_required_capabilities",
      "capability_waiver_help": "waiver_help",
      "resource_report_status": "resource_status"
    }
  },
  "project": {
    "class": "ProjectInitializationInputs",
    "module": "project/initialization_inputs.py",
    "constructor": "none",
    "instance": "_project_initialization_inputs",
    "methods": {
      "project_types_from_manifest": "types_from_manifest",
      "project_type_allows_processforge_core": "allows_core",
      "project_type_is_meta_workspace": "is_meta_workspace",
      "project_mode": "mode",
      "project_defaults": "defaults"
    }
  }
}
```
Constants:
```json
{
  "PROCESSFORGE_CORE_PROJECT_TYPES": "project.initialization_inputs",
  "META_PROJECT_TYPES": "project.initialization_inputs"
}
```
## journal

Create authoring/journals.py AuthoringJournalStore() with write_data(path,journal) and write(plan,journal), TWO full originals. Reuse ready common.text.ensure_trailing_newline, common.yaml_dump.dump_yaml, AuthoringPlan from authoring.plans and AuthoringInputService().journal_path. Preserve parent mkdir BEFORE UUID creation and try; exact .<name>.<uuidhex>.tmp sibling, write_text UTF8, os.replace, finally exists then unlink, including exception/cleanup precedence. Do not replace with another atomic writer whose observations differ, no fsync/retry/rollback/lock changes. Concrete inputs stored cold or instantiated at exact call, no Main callback. Keep model callbacks inert; this bounded journal storage does not migrate authoring preflight/effects/publication/rollback/failure execution. Native tests stub filesystem/UUID/replace only, max five. Parent will use real scratch writes and a replace failure. Preserve complete original AST/literals beyond declared name/self/concrete owner substitutions, future/signature/annotation strings, guard/read/check/write/cleanup order, native errors and causes, unknown fields/aliasing/live reads. Constructors cold and roots explicit. No Main/Host imports/callback/provider/Any facade back to Main, duplicated ready parser/path/digest/merge behavior, new features/policies/permissions/cache/DI/framework, lifecycle/transaction semantics changes, external network/workplace writes, Git/remotes/infrastructure/nested agents/self transitions. Only own exact assigned products/artifacts/scratch; never Main/docs/inventory or peer products. Read pinned architecture/PF Python/full frozen inputs first. Compile without product import; at most five meaningful synthetic cases, no successful repeats. Parent performs actual scratch/default/copied Core/affected scripts. Russian report and proof.json status passed; algorithms every assigned original full_ast_equal/signature_equal/annotations_equal true; products each owned path=>rawSHA; prior_owners only unchanged canonical dependencies raw_equal/ast_equal true (consumer beforeimages are mutable products owned by declared peers); synthetic_cases<=5 status passed. Retain complete normalized AST/proof. For each actual assigned consumer, report consumer_preservation full_ast_equal/raw_only_declared_changes/assertions_unchanged/fixtures_unchanged/no_eager_bootstrap_regression true. No assertions/fixtures/guards or unselected behavior may change. Exactly one final newline.

## parameters

Create configuration/parameter_sources.py ParameterSourceService() with record(source_id,layer,parameters,*,path=None,project_root=None,private=False,display_path=None), workplace_paths(workplace_manifest), add(result,*,all original args), process_parameters(path), requirements_fingerprints(flow_root,project_root). FIVE entire originals. Use canonical common.paths.rel/path_is_relative_to, common.values.parameter_payload, FileDigestReader.sha256_file, ContextContractInputs.load_yaml_document, ParameterMergePolicy.merge_maps. workplace_paths uses WorkspacePathReferenceReader(workplace_root,workplace_root,workplace_manifest=manifest).resolve_registry_relative_path with original explicit args, no dummy/current root; preserve load/read counts and default-path dedup. Record retains sorted string keys, private display marker precedence, guarded digest and unknowns. add retains append-before-merge, empty no-op, in-place result/provenance and merge errors; no new copy/guard. requirements_fingerprints preserves unused project_root parameter. Also own src/processforge_core/work/context.py: replace EXACT THREE core.add_parameter_source calls in build_context_fields with direct concrete ParameterSourceService().add or a single operation-local cold instance. Add canonical import at module scope (already real Core package), preserve every other AST node/raw byte, no changed signature/guards/fields/provenance/order/legacy calls. Selected code must not call old core.add_parameter_source. Full consumer AST/raw proof mandatory; unselected legacy responsibilities remain explicitly unselected. Preserve complete original AST/literals beyond declared name/self/concrete owner substitutions, future/signature/annotation strings, guard/read/check/write/cleanup order, native errors and causes, unknown fields/aliasing/live reads. Constructors cold and roots explicit. No Main/Host imports/callback/provider/Any facade back to Main, duplicated ready parser/path/digest/merge behavior, new features/policies/permissions/cache/DI/framework, lifecycle/transaction semantics changes, external network/workplace writes, Git/remotes/infrastructure/nested agents/self transitions. Only own exact assigned products/artifacts/scratch; never Main/docs/inventory or peer products. Read pinned architecture/PF Python/full frozen inputs first. Compile without product import; at most five meaningful synthetic cases, no successful repeats. Parent performs actual scratch/default/copied Core/affected scripts. Russian report and proof.json status passed; algorithms every assigned original full_ast_equal/signature_equal/annotations_equal true; products each owned path=>rawSHA; prior_owners only unchanged canonical dependencies raw_equal/ast_equal true (consumer beforeimages are mutable products owned by declared peers); synthetic_cases<=5 status passed. Retain complete normalized AST/proof. For each actual assigned consumer, report consumer_preservation full_ast_equal/raw_only_declared_changes/assertions_unchanged/fixtures_unchanged/no_eager_bootstrap_regression true. No assertions/fixtures/guards or unselected behavior may change. Exactly one final newline.

## reports

Create project/report_read.py ReportProjectionReader() methods section_items(path,marker), section_has_items(path,marker), has_missing_required_capabilities(path), waiver_help(), resource_status(project_root,kind,resource_id): FIVE complete originals. Reuse ProjectMetadataReader(root).flow_root, common.ids.safe_id, common.paths.rel. Preserve exact Markdown splitting/first marker/next heading, UTF8 replacement, ignored - None., boolean wrapper, exact waiver help multiline literal, report path/safeID, SKIP/missing vs WARN/no Result and first regex result. Also own tools/smoke_remediation_aggregate_gates.py: migrate THREE processforge.resource_report_status read/write/restore bindings to canonical ReportProjectionReader.resource_status class method. Add direct canonical class import AFTER existing import processforge bootstrap; when replacing lambda add its required ignored self argument so class binding passes the same three original operation args. Keep try/finally restoration and every assertion/fixture/mock-other-commands/release-gate selection unchanged. No test scenario repeats; this is only actual consumer binding migration. No eager Core before existing processforge bootstrap. Preserve complete original AST/literals beyond declared name/self/concrete owner substitutions, future/signature/annotation strings, guard/read/check/write/cleanup order, native errors and causes, unknown fields/aliasing/live reads. Constructors cold and roots explicit. No Main/Host imports/callback/provider/Any facade back to Main, duplicated ready parser/path/digest/merge behavior, new features/policies/permissions/cache/DI/framework, lifecycle/transaction semantics changes, external network/workplace writes, Git/remotes/infrastructure/nested agents/self transitions. Only own exact assigned products/artifacts/scratch; never Main/docs/inventory or peer products. Read pinned architecture/PF Python/full frozen inputs first. Compile without product import; at most five meaningful synthetic cases, no successful repeats. Parent performs actual scratch/default/copied Core/affected scripts. Russian report and proof.json status passed; algorithms every assigned original full_ast_equal/signature_equal/annotations_equal true; products each owned path=>rawSHA; prior_owners only unchanged canonical dependencies raw_equal/ast_equal true (consumer beforeimages are mutable products owned by declared peers); synthetic_cases<=5 status passed. Retain complete normalized AST/proof. For each actual assigned consumer, report consumer_preservation full_ast_equal/raw_only_declared_changes/assertions_unchanged/fixtures_unchanged/no_eager_bootstrap_regression true. No assertions/fixtures/guards or unselected behavior may change. Exactly one final newline.

## project

Create project/initialization_inputs.py ProjectInitializationInputs() owning types_from_manifest(data), allows_core(data), is_meta_workspace(data), mode(project_root,answers), defaults(project_root,answers,detected): FIVE complete originals. Move EXACT PROCESSFORGE_CORE_PROJECT_TYPES/META_PROJECT_TYPES assignments here; Main imports same names for remaining consumers. Reuse common.ids.safe_id, no duplicate sanitization. Preserve repeated manifest/project.get truthiness, list/item order/filter/duplicates, exact allowed sets, explicit greenfield/brownfield shortcut before exists, hidden-directory exclusion set, directory/file native errors; detected project_kind indexing/unknown, requested type/type_hint/auto order and all unknown/native errors. Existing ProjectCoordinationReader.project_mode/project_defaults are DIFFERENT coordination contracts and must remain unchanged; project_mode JSON strings also stay unchanged. Also own project/initialization.py replace its one actual core.project_mode(root,normalized["answers"]) call with direct ProjectInitializationInputs().mode, canonical Core import, no other changes. That operation remains legacy for unselected build/apply responsibilities. Preserve all guard/plan/apply lambdas/output AST, no new permission, root creation or effect. Preserve complete original AST/literals beyond declared name/self/concrete owner substitutions, future/signature/annotation strings, guard/read/check/write/cleanup order, native errors and causes, unknown fields/aliasing/live reads. Constructors cold and roots explicit. No Main/Host imports/callback/provider/Any facade back to Main, duplicated ready parser/path/digest/merge behavior, new features/policies/permissions/cache/DI/framework, lifecycle/transaction semantics changes, external network/workplace writes, Git/remotes/infrastructure/nested agents/self transitions. Only own exact assigned products/artifacts/scratch; never Main/docs/inventory or peer products. Read pinned architecture/PF Python/full frozen inputs first. Compile without product import; at most five meaningful synthetic cases, no successful repeats. Parent performs actual scratch/default/copied Core/affected scripts. Russian report and proof.json status passed; algorithms every assigned original full_ast_equal/signature_equal/annotations_equal true; products each owned path=>rawSHA; prior_owners only unchanged canonical dependencies raw_equal/ast_equal true (consumer beforeimages are mutable products owned by declared peers); synthetic_cases<=5 status passed. Retain complete normalized AST/proof. For each actual assigned consumer, report consumer_preservation full_ast_equal/raw_only_declared_changes/assertions_unchanged/fixtures_unchanged/no_eager_bootstrap_regression true. No assertions/fixtures/guards or unselected behavior may change. Exactly one final newline.

## Primary assurance and delivery

Remove 17 functions/two constants, retain 671 Main definitions. Compose four cold services, all actual consumer targets migrated together. Verify full Main AST, constant equality, complete consumer raw/AST boundaries and ready owner reuse. Native synthetic proofs max five per role retained without repeats. Parent real scratch/default/copy: journal serialization/replace failure/cleanup precedence; private parameter provenance/merge/live reads, report parsing/native errors, project defaults/modes/types. Existing focused scripts only; no archive/Runtime/installed/connected-host/ZIP checks. Final independent raw-hash review, scoped commit/parallel dual dev push/readback using existing GitVerse token with helpers/traces disabled, terminal Works/root doctor. Reread all original architecture after delivery. At 09:00 stop new admissions, finish in-flight and night report.
