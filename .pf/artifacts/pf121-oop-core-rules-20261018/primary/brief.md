# OOP Core rules: bounded implementation and delivery plan

Baseline: `4ace0657958603e50446e875db8cc6b57d5edbe9`. Four native shell Core writers, primary sole monolith/caller/docs/inventory integrator, one independent clean-context reviewer after implementation and focused assurance. Continue existing 1.2.0 source refactor; no new functionality. User-authorized overnight run ends at 2026-10-19 09:00 device time, then finish current tasks. No ZIP contents, broad release/archive/install checks or infrastructure operations.

## Architecture and domain

Original architecture and progressive decision were fully reread after both previous delivered slices. The approved direction remains transports -> concrete Core owners -> Core/primitives. These are existing document-building and policy responsibilities. Each new class is a stateless concrete policy/builder; choose normal instance methods, no container or per-function facade. Direct normal Core use must not import tools.processforge, CLI/Host objects or callbacks. Keep existing package initializers unchanged. Preserve algorithms, unknown fields, mutation/aliasing, errors/guard order, dict/list ordering and external CLI/MCP schemas/exit/messages.

Four nonoverlapping product scopes and concrete method mappings are below. Keep original signatures/defaults, including required title in authoring.defaults; only add self. The frozen baseline-functions.json records every source body (including both temporal as_list definitions) and original constants. Methods must call the concrete owning method/primitives, with no obsolete internal wrappers. Constants retain original set/list types and values. Shared normal primitives stay functions.

```json
{
  "authoring": [
    "src/processforge_core/process_catalog/authoring.py",
    "src/processforge_core/common/ids.py",
    "src/processforge_core/common/values.py"
  ],
  "evolution": [
    "src/processforge_core/process_catalog/evolution.py",
    "src/processforge_core/common/checks.py"
  ],
  "drivers": [
    "src/processforge_core/runtime/drivers.py"
  ],
  "sites": [
    "src/processforge_core/maintenance/sites.py"
  ],
  "review": []
}
```

```json
{
  "ProcessEvolutionPolicy": {
    "default_evolve_block": "default_block",
    "normalize_evolve_block": "normalize_block",
    "validate_evolve_block": "validate_block"
  },
  "ProcessAuthoringDefinitionBuilder": {
    "default_process_authoring_answers": "defaults",
    "normalize_process_authoring_answers": "normalize",
    "process_from_authoring_answers": "build",
    "normalize_process_transitions": "normalize_transitions",
    "materialize_process_responsibility_boundaries": "materialize_responsibility_boundaries"
  },
  "RuntimeDriverDefinitionPolicy": {
    "default_runtime_driver_documents": "default_documents",
    "default_runtime_driver_registry": "default_registry",
    "driver_placeholder_errors": "placeholder_errors",
    "parse_runtime_driver_limits": "parse_limits",
    "runtime_driver_start_readiness_checks": "start_readiness",
    "validate_runtime_driver_document": "validate"
  },
  "UpdateSitePolicy": {
    "update_location": "location",
    "update_source_kind": "source_kind",
    "update_site_source_id": "source_id",
    "update_site_stable_key": "stable_key",
    "derived_update_site_record": "record",
    "update_site_policy": "policy"
  }
}
```

Authoring creates common.values and updates common.ids first. Evolution creates common.checks first. Authoring uses a concrete ProcessEvolutionPolicy instance as its collaborator (constructor may take no args and own the concrete collaborator; no provider/callback). Evolution/driver import Check/check from common.checks. Keep Check a mutable dataclass with exactly level/message and check uppercasing at construction; no frozen DTO. Canonical safe_id already exists in common.ids unchanged; add exact title_from_id there. common.values.as_list is the effective LATE strict-list helper (scalar -> []), common.values.string_list is the exact current helper including repeated str evaluation. Keep both monolith as_list definitions intact; primary removes the old safe_id/title_from_id/string_list/Check/check definitions and imports canonical bindings for all remaining users. The earlier artifact-declaration owner can reuse common.values helpers with exact behavior and no wrappers.

Authoring preserves fresh defaults, all existing deepcopy locations and transition shared_return alias across routes; full schema/authoring validation stays in monolith. Evolve preserves enabled/disabled truthiness, nested shallow merging, privacy/apply retention and check order/messages. Drivers preserve fresh built-in metadata dicts, placeholder recursion order and native errors, integer/bool validation and current args normalization; start_readiness does no executable I/O/probing. Sites preserve ignored provider_key, raw nonblank id, shallow policy mutation, override/channel references and exact rel behavior; no auth expansion/network/I/O. Actual runtime start, update/install, registry and schema validation remain legacy.

## Integration, assurance and delivery

Primary waits for all four code reports before editing the monolith. Primary updates every mapped Name consumer and constant owner import, plus the only two known external function consumers in smoke_codex_worker_governance.py and smoke_prepared_execution_context.py. No old aliases. Primary updates EN/RU ownership documentation and only the shipped inventory rows for these 14 product paths, preserving three known unrelated inventory mismatches. Record exact changed hashes.

Use a bounded temporary frozen-source comparison harness for defaults, branches, weird/native errors and relevant alias/mutation behavior. Verify direct and copied Core without CLI/Host. Run each affected existing smoke once, in primary-owned scratch with short paths; no fixture smokes inside shell workers (known restricted fixture creation). Choose affected authoring/evolve/runtime driver/update-site and helper consumer tests after bounded search. Preserve raw results; fix collection of descriptive PASS lines without rerunning successes. No permanent new tests or blanket suites. Reviewer starts after all product edits/checks and accepts exact hashes; no mutations afterward without focused re-review. Report skipped symlink/environment limits accurately.

Every substantive result is logged in role report and night log. Complete native process stages using exact selectors/capsule and actual evidence. Commit explicit product and bounded public PF evidence paths only, preserve unrelated dirty files/index, push same commit to origin/dev and gitverse/dev and verify exact SHA. GitVerse uses existing GITVERSE_TOKEN via private process environment and no credential helper. No credentials/private device paths in public artifacts. Finish native release/evolve and terminal doctor; reread original architecture after the completed major task before admitting another. Source-only acceptance is separate from archive/install/Runtime/connected-host evidence; OOP-01..05 epics remain open.
