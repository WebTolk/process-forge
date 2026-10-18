# Work fields, coordination reads, privacy and update-source contracts

Baseline: `201ed9a677aca13d5df53d6de78b09fbe46bcf47`. Previous source slice is delivered to both dev remotes, all six Works terminal and root doctor passed. Original architecture/specs were reread. Primary is the sole caller/Host/docs/inventory integrator; four native shell writers own the disjoint paths below. One independent clean-context reviewer follows completed implementation and final focused assurance. Work/privacy/updates use high, coordination medium, reviewer high. No nested agents.

## Architecture and exact existing responsibilities

Preserve released 1.2.0 CLI/MCP/formats and all original algorithms, data/unknown fields, aliases/mutations, guards/order/messages/native failures, current reads and identity/access boundaries. Concrete Core owners use existing Core/primitives with no path back to monolith/CLI/Host through callbacks/providers/Any-core. Reuse ContextContractInputs; do not create a new wrapper class for these fields. No new permissions, scanner rules, trust policy, schema engine, Kernel/container, feature or MCP resources. D01/D02/D03/D06/D09/D11 and D07/R01-R12 retain their existing contracts. Lifecycle, authorization and schema-based validation stay with their existing owners. Source-only proof does not complete epics or other delivery layers.

```json
{
  "work": [
    "src/processforge_core/work/context_documents.py"
  ],
  "coordination": [
    "src/processforge_core/project/coordination.py"
  ],
  "privacy": [
    "src/processforge_core/common/privacy.py",
    "src/processforge_core/evolution/privacy.py",
    "src/processforge_core/documents/answers.py"
  ],
  "updates": [
    "src/processforge_core/maintenance/source_contracts.py"
  ],
  "review": []
}
```

```json
{
  "ContextContractInputs": {
    "normalize_assignment_path": "normalize_assignment_path",
    "assignment_path_key": "assignment_path_key",
    "assignment_scope_items": "assignment_scope_items",
    "assignment_write_scope": "assignment_write_scope",
    "assignment_has_glob": "assignment_has_glob",
    "assignment_allows_write_scope_overlap": "assignment_allows_write_scope_overlap",
    "assignment_dependency_set": "assignment_dependency_set",
    "validate_assignment_required_sources": "validate_assignment_required_sources",
    "capsule_coordination_block": "capsule_coordination_block",
    "path_allowed_by_scope": "path_allowed_by_scope"
  },
  "ProjectCoordinationReader": {
    "normalize_project_coordination_mode": "project_mode",
    "normalize_workplace_default_project_mode": "workplace_mode",
    "default_workplace_coordination": "workplace_defaults",
    "default_project_coordination": "project_defaults",
    "workplace_coordination_config": "workplace",
    "project_coordination_config": "project"
  },
  "EvolvePrivacyPolicy": {
    "evolve_sanitizer_findings": "findings",
    "evolve_sanitize_text": "text",
    "evolve_sanitize_value": "value"
  },
  "UpdateSourceContractPolicy": {
    "source_requires_https": "requires_https",
    "valid_remote_url_shape": "remote_url_shape",
    "valid_artifact_url_shape": "artifact_url_shape",
    "append_env_reference_checks": "append_env_checks",
    "append_update_source_checks": "append_source_checks",
    "validate_update_source_registry_data": "validate_registry",
    "sorted_update_sources": "sorted_sources"
  }
}
```

Every new implementation module MUST include the original `from __future__ import annotations`. Preserve existing module settings. Compare actual annotation mappings as well as AST/signatures before review. Current known gaps in previous cycles were corrected before acceptance; do not repeat them.

Work: ContextContractInputs already owns normalize_assignment_path and assignment_scope_items. Reuse those methods unchanged; main removes only their two obsolete monolith wrappers. Add the other eight mapped methods with exact original signatures/defaults plus self; preserve its frozen dataclass fields, constructor, decorators and all previous method bodies. Use self calls, canonical common.values.as_list/common.ids.safe_id and stdlib os/fnmatch. Keep platform path keys, list filtering/dedup/order, empty scopes, glob special cases, dependency truthiness and current required-source file observations. Capsule coordination retains nested references, raw allowed_message_types, bool/short-circuit semantics and original simple/organized refusal. No access expansion or new guard.

Coordination: ProjectCoordinationReader has a concrete YamlDocumentReader(_parse_simple_yaml) default and uses ProjectMetadataReader(project_root).flow_root(). Construction performs no I/O, retains no project/Work/parsed data. Keep all six algorithms and three constants, shallow director defaults/merges, unknown fields, current existence/load checks and normalization/refusal behavior. Effective coordination assembly and actual Director operations remain legacy.

Privacy: common.privacy owns two small functional predicates plus exact BACKSLASH/LOCAL_PATH_PATTERNS/SECRET_VALUE_PATTERNS (the last currently defined in documents.answers). AnswersDocumentReader imports canonical pattern data and retains its entire class algorithm/strict errors. EvolvePrivacyPolicy owns findings/text/value recursively using canonical primitives; do not sanitize keys/tuples or add checks/copying. Preserve all regex bytes/flags, evaluation order, thresholds, set sorting and unchanged-object returns.

UpdateSourceContractPolicy owns only seven current pure helper/registry/sorting methods and UPDATE_SUBJECT_TYPES, CONTROL_CHAR_RE, ENV_REFERENCE_RE. Preserve caller list identity/mutation, weird types/truthiness/native errors, error text/order, source/URL/env rules and stable sorting. Full normalized-manifest/overrides schema validation and actual update operations remain legacy; they call the moved helpers.

## Consumers, focused proof and delivery

Primary migrates all moved Name consumers in tools/processforge.py and canonical imports for shared primitives/data. Known actual external consumers: work/context.py capsule compilation, Host final secret predicate, authenticated-report-content smoke and Work-start-scope smoke. Existing ScopeConflictService already calls ContextContractInputs and needs no edits. Update only actual calls, preserving caller order and all unrelated code.

Host preserves exact short circuit: automatic content/body and metadata filters deny first; only after they pass, lazy-import canonical contains_secret_value and evaluate it at the same final guard position, returning the same unsafe_automatic_content denial. No auth/provenance/attempt/hash/owned-report logic changes. Preserve standalone bootstrap timing. Core compiler calls ContextContractInputs directly at the existing capsule projection site; full context assembly still has legacy dependencies.

Contributors use bounded compile/AST comparison, no fixtures or permanent tests. Primary owns temporary focused old/new cases for metadata/paths/empty scopes, privacy/URL native failures and aliasing, coordination live I/O, normal direct/copied Core plus affected existing Work/coordination/privacy/update/Host smokes in its own scratch. Preserve original future annotations. No blanket release checks, ZIP contents, archive/install/Runtime/connected-host qualification, environment retries or infrastructure actions. Reviewer checks final actual bytes/evidence and pins exact hashes; any later source change needs scoped re-review.

Update EN/RU ownership docs and only changed/new shipped checksum rows, preserving unrelated drift. Commit explicit owned paths/evidence, preserve unrelated index/work, push identical SHA to origin/dev and gitverse/dev with exact readback. Existing GITVERSE_TOKEN is mandatory for GitVerse and credential helper is disabled; never expose/store it. Complete exact native release/evolve and root doctor; reread original architecture before another bounded scope. Stop starting tasks at 2026-10-19 09:00 device time, finish current work and report the night.
