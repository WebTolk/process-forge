# Output readiness, driver selection, platform projections and authoring checks

Baseline: `eef4f953d935294d31d9579bc1d9eeb0d572fb94`. Prior slice delivered identically to both dev remotes; all six Works terminal, root doctor passed, product/index clean. Original architecture fully reread and context fresh/ready. Sequential 1-1-4: primary alone owns monolith/ProcessExecutionService/Host/service/smoke/docs/inventory integration; four native workers own disjoint products, reviewer follows final QA. Outputs/runtime/authoring/review high; straightforward pure platform projections medium. No nested agents.

Preserve released 1.2.0 CLI/MCP/errors/formats, original algorithms/defaults/future annotations, native errors/order/unknowns/current reads and identity/access. Use concrete Core owners only, no backward imports/providers/Any-core facade. Reuse existing classes; no Kernel/DI/plugin framework, new permission/feature/MCP resources or infrastructure change. D01/D02/D03/D06/D09/D11 and D07/R01-R12 remain within existing bounds. No lifecycle/locks/journals/recovery/launch reimplementation.

Ownership:
```json
{
  "outputs": [
    "src/processforge_core/work/outputs.py"
  ],
  "runtime": [
    "src/processforge_core/runtime/selection.py",
    "src/processforge_core/project/metadata.py",
    "src/processforge_core/common/json_io.py"
  ],
  "platform": [
    "src/processforge_core/project/platform_policy.py"
  ],
  "authoring": [
    "src/processforge_core/process_catalog/validation.py",
    "src/processforge_core/common/privacy.py"
  ],
  "review": []
}
```

Methods:
```json
{
  "outputs": {
    "class": "WorkOutputPolicy",
    "module": "work/outputs.py",
    "existing": true,
    "methods": {
      "required_output_checks": "checks",
      "task_verification_fingerprint": "fingerprint"
    }
  },
  "runtime": {
    "class": "RuntimeDriverSelectionService",
    "module": "runtime/selection.py",
    "methods": {
      "runtime_driver_for_task": "for_task",
      "runtime_driver_for_worker_state": "for_worker_state"
    }
  },
  "platform": {
    "class": "PlatformContractPolicy",
    "module": "project/platform_policy.py",
    "methods": {
      "normalize_platform_ref": "normalize_ref",
      "platform_refs_from": "refs",
      "contract_required_platforms": "required_platforms",
      "contract_extends": "extends",
      "contract_required_capabilities": "required_capabilities",
      "contract_required_items": "required_items",
      "contract_includes": "includes",
      "contract_recommended_items": "recommended_items",
      "contract_optional_items": "optional_items"
    }
  },
  "authoring": {
    "class": "ProcessAuthoringValidationService",
    "module": "process_catalog/validation.py",
    "methods": {
      "validate_process_authoring_logic": "logic",
      "validate_process_definition_files": "files",
      "process_companion_paths": "paths"
    }
  }
}
```

Special canonical owners:
```json
{
  "project_workplace_manifest": "ProjectMetadataReader(project_root).workplace_manifest()",
  "json_read": "processforge_core.common.json_io.json_read",
  "public_yaml_has_private_path": "processforge_core.common.privacy.public_yaml_has_private_path"
}
```

## outputs

Extend EXISTING frozen WorkOutputPolicy with exactly checks and fingerprint from frozen functions. Preserve all prior five methods/fields/constructor/decorators byte/AST semantics. Reuse self.inputs, self.task_path/self.path, canonical Check/check/safe_id/rel/hashlib/json. Preserve optional early skip, waivers truthiness and alias precedence, absence/invalid/missing/pending distinctions, current is_file/read_bytes observations and guard/order/errors, duplicate expected-report inputs and exact JSON/hash encoding. Do not add containment/authorization or change which outputs are read. Parent removes old definitions, adds independent optional typed callable seams to ProcessExecutionService and migrates all consumers; do not edit them. Preserve original from __future__ import annotations and actual annotation maps; project_root consumed by bound metadata owner is the explicitly planned binding change. Own only assigned products/artifacts/scratch. No Git mutation, remote/infrastructure action, lifecycle transition, nested agents, permanent tests or fixture suite. Read exact valid Work/capsule, frozen baseline, brief/Core AGENTS. Complete normalized AST/signature/annotation proof, existing class preservation and optionally 3-5 meaningful pure synthetic cases only. Parent handles final default imports, live wiring and existing smokes. Russian report with actual hashes and limits.

## runtime

Create RuntimeDriverSelectionService(distribution_root: Path) with exact for_task/for_worker_state algorithms and concrete RuntimeDriverCatalogReader, RuntimeDriverDefinitionPolicy, WorkPaths and canonical json_read. Extend EXISTING ProjectMetadataReader with workplace_manifest(self), using its bound project_root and documents, to own exact old local-only project_workplace_manifest algorithm; preserve prior fields/constructor and every prior method. Do not confuse it with broader resolve_project_workplace_manifest. Absolute manifest paths are not newly resolved; preserve local config read/truthiness/expanduser ordering. Create common/json_io.py with exact shared json_read function (is_file -> empty, otherwise json.loads/read_text with native failures and raw returned types). No caches or catch changes. Preserve direct-path deep copy/_driver_ref, current saved command read, fallback order, validation message/error cause ordering. No current project captured by long-lived selection service; explicit arguments per operation. Preserve original from __future__ import annotations and actual annotation maps; project_root consumed by bound metadata owner is the explicitly planned binding change. Own only assigned products/artifacts/scratch. No Git mutation, remote/infrastructure action, lifecycle transition, nested agents, permanent tests or fixture suite. Read exact valid Work/capsule, frozen baseline, brief/Core AGENTS. Complete normalized AST/signature/annotation proof, existing class preservation and optionally 3-5 meaningful pure synthetic cases only. Parent handles final default imports, live wiring and existing smokes. Russian report with actual hashes and limits.

## platform

Create PlatformContractPolicy(catalog: PlatformContractReader) with exactly nine mapped pure projection methods. The explicit concrete catalog is used only for canonical contract_id; no dummy root, static conversion, copying ID rules, monolith callback, hierarchy resolver or package catalog migration. Reuse common.values.list_value. Preserve string vs mapping refs, default_required raw/bool distinction, alias precedence, version truthiness/coercion, required is True identity tests, raw includes string early return, sorting/dedup/native errors and evaluation order. Constructor retains only concrete Core catalog, no I/O or current Work/project. Preserve original from __future__ import annotations and actual annotation maps; project_root consumed by bound metadata owner is the explicitly planned binding change. Own only assigned products/artifacts/scratch. No Git mutation, remote/infrastructure action, lifecycle transition, nested agents, permanent tests or fixture suite. Read exact valid Work/capsule, frozen baseline, brief/Core AGENTS. Complete normalized AST/signature/annotation proof, existing class preservation and optionally 3-5 meaningful pure synthetic cases only. Parent handles final default imports, live wiring and existing smokes. Russian report with actual hashes and limits.

## authoring

Create ProcessAuthoringValidationService with exact logic/files/paths algorithms, concrete default ProcessEvolutionPolicy and ProcessArtifactDeclarationPolicy and exact ERROR_WORKFLOW_MODES/ERROR_WORKFLOW_FALLBACKS/ITERATION_KINDS data. Preserve all ordering, nested id_values and warning/refusal messages, native failures, compound early branches, companion-root truthiness/defaults and is_file short circuits. Append exact public_yaml_has_private_path primitive to EXISTING common.privacy using canonical is_public_path_safe plus json.dumps; preserve all prior privacy definitions/data. Parent removes old monolith helper/constants and migrates consumers; no aliases. Full validate_process_contract and process route/catalog metadata remain legacy. Preserve original from __future__ import annotations and actual annotation maps; project_root consumed by bound metadata owner is the explicitly planned binding change. Own only assigned products/artifacts/scratch. No Git mutation, remote/infrastructure action, lifecycle transition, nested agents, permanent tests or fixture suite. Read exact valid Work/capsule, frozen baseline, brief/Core AGENTS. Complete normalized AST/signature/annotation proof, existing class preservation and optionally 3-5 meaningful pure synthetic cases only. Parent handles final default imports, live wiring and existing smokes. Russian report with actual hashes and limits.

## Primary composition contract and assurance

ProcessExecutionService currently takes two optional capabilities from its legacy core. Replace ONLY those with independent typed callable keyword-only fields `output_checks` and `verification_fingerprint`, canonical WorkOutputPolicy bound methods by default, explicit None for unavailable. Use field(default_factory=..., kw_only=True, repr=False, compare=False), preserve frozen class, three positional args and all existing fields/methods except exact automation factory wiring. Existing AutomationReadinessService ports/check order/reasons stay unchanged. Other legacy capabilities (event paths/latest event) stay unchanged and lazy. No new business capability or behavior; normal application always had both helpers. Known fake consumers must pass explicit callable/None seams, preserving unavailable/lazy/exception identity assertions. Test-only retained-baseline adapter may select kwargs by dataclass field presence; do not add product compatibility aliases.

Primary removes nineteen old definitions/three constants, imports canonical privacy/json functions, rewrites seven direct `project_workplace_manifest(project_root)` calls as `ProjectMetadataReader(project_root).workplace_manifest()`, and migrates all actual consumers including Host/service and existing smokes. No first-class workplace helper references were found. Preserve Host bootstrap/guard timing with lazy imports at prior call sites, all arguments and refusal order. Do not run full recovery/runtime suites just for unchanged path calls; focused existing checks only.

Use complete AST and actual annotation maps (metadata binding explicitly consumes project_root), preserved existing classes, normal direct/copied Core without transport, a few live output/metadata/driver cases and existing automation/output/worker/authoring/platform smokes on final bytes. Primary owns fixture execution; retain successful output, recognize PASS with colon/space/JSON and resume only unrun checks. No permanent tests, broad release/archive/install/Runtime/connected-host/ZIP checks or environment/ACL repairs. Reviewer pins exact final hashes; any later source change needs bounded re-review.

Update EN/RU ownership and only affected/new checksum rows. Preserve known unrelated drift, dirty state and index. Commit exact owned paths/portable proof, push same SHA to origin/dev and gitverse/dev and read full SHA from both. GitVerse only existing GITVERSE_TOKEN, credential helper disabled; never print/store token. Complete six native Works/root doctor and reread original architecture before next scope. Source-only acceptance does not close OOP epics. Stop admitting tasks at 2026-10-19 09:00 device time, finish current tasks and report the night.
