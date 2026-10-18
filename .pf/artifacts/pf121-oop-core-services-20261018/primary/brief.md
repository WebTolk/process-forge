# Core services: existing presentation, catalog and selection responsibilities

Baseline: `0a8b5029a1cf5cd1afc0e33d545af6351b4e7261`. Prior four-owner slice is delivered to both dev remotes and all six Works are terminal; original migration contract, progressive decision, clarification, ADR/domain/direction and OOP-02/03/05 were reread. New valid root Work grants the primary only callers/docs/inventory and its evidence. Four native writers own disjoint Core paths; reviewer starts after code, focused assurance and docs. Presentation uses medium effort, driver/candidate/update work and review high. No nested agents or parallel writers on a file.

## Domain, architecture and concrete APIs

Preserve existing 1.2.0 external contracts. These are current process-definition presentation/reverse projection, runtime driver document reads, knowledge candidate targeting and update-version rules. Transports/monolith call concrete Core owners; owners use existing Core primitives/readers. No monolith callback/provider/Any-core, Kernel/container/plugin, permission changes or new MCP-resource functionality. D01/D02/D03/D06/D09/D11 apply to ownership/composition/consumers; D07 and R01-R12 preserve live reads, existing refusal/identity/binding/order and evidence. No new authorization or lifecycle authority is introduced. Pure builders/renderers keep I/O outside; driver reader retains only original read behavior. Source-only evidence is separate from delivery layers; epics remain open.

```json
{
  "presentation": [
    "src/processforge_core/process_catalog/authoring.py",
    "src/processforge_core/process_catalog/presentation.py",
    "src/processforge_core/process_catalog/coordination.py"
  ],
  "drivers": [
    "src/processforge_core/runtime/catalog.py"
  ],
  "candidates": [
    "src/processforge_core/evolution/__init__.py",
    "src/processforge_core/evolution/candidates.py"
  ],
  "updates": [
    "src/processforge_core/maintenance/versions.py",
    "src/processforge_core/maintenance/presentation.py"
  ],
  "review": []
}
```

```json
{
  "ProcessAuthoringDefinitionBuilder": {
    "process_to_authoring_answers": "from_definition"
  },
  "ProcessAuthoringRenderer": {
    "render_authoring_questions": "questions",
    "render_logic_review": "logic_review",
    "render_process_agent_prompt": "agent_prompt",
    "render_process_doc": "document"
  },
  "RuntimeDriverCatalogReader": {
    "runtime_driver_registry_paths": "registry_paths",
    "runtime_driver_entries": "entries",
    "runtime_driver_entry_path": "entry_path",
    "load_runtime_driver_by_path": "load_path",
    "registered_runtime_driver_path": "registered_path",
    "resolve_runtime_driver": "resolve",
    "runtime_driver_ref_is_direct_path": "ref_is_direct_path",
    "normalized_runtime_driver_ref": "normalized_ref",
    "runtime_driver_id_list": "ids"
  },
  "KnowledgeCandidateTargetingPolicy": {
    "candidate_id_from_data": "id_from_data",
    "candidate_target": "target",
    "candidate_target_type": "target_type",
    "candidate_target_id": "target_id",
    "candidate_routing_destination": "routing_destination",
    "candidate_destination_matches": "destination_matches",
    "candidate_promotion_status": "promotion_status",
    "candidate_generalization_level": "generalization_level",
    "candidate_is_parent_promotion_candidate": "is_parent_promotion_candidate",
    "candidate_ready_for_curated_package": "ready_for_curated_package",
    "validate_candidate_targeting": "validate"
  },
  "UpdateVersionSelectionPolicy": {
    "latest_update_version": "latest",
    "normalize_manifest_versions": "normalize",
    "selected_update_version": "select",
    "update_candidate_id": "candidate_id"
  },
  "UpdateAssessmentRenderer": {
    "render_update_assessment": "render"
  }
}
```

Use ordinary instance methods with exact original parameters/defaults plus self. Existing ProcessAuthoringDefinitionBuilder gains from_definition only; keep all earlier method bodies and constructor unchanged. ProcessAuthoringRenderer uses the small canonical process_coordination_requirements function and PROCESS_COORDINATION_MODES from process_catalog.coordination. This primitive remains a function rather than a needless class wrapper. Primary removes its old definition and imports the canonical function/constant for all remaining consumers. Preserve exact text/newlines and eager default-expression evaluation.

RuntimeDriverCatalogReader(distribution_root: Path) retains the supplied immutable root value without coercion/resolve/I/O, concrete YamlDocumentReader(_parse_simple_yaml), RuntimeDriverDefinitionPolicy. Normal direct use requires only the actual root Path, never a CLI/Host object. registry_paths uses ProjectMetadataReader(project_root).flow_root(); entries uses documents.load; load_path keeps original existence guard before documents.read and setdefault(_source_path). Keep strict/tolerant split, live reads without cache, first match, id-list overwrite/sorted output, path and malformed YAML errors. Existing reader read and monolith strict loader have the same default YAML error behavior. No writes or actual Runtime process operations move.

KnowledgeCandidateTargetingPolicy owns only the eleven existing pure targeting/identity/routing/promotion/validation methods and three constants. Import existing EVOLVE_CANDIDATE_TARGETS, Check/check, safe_id/string_list canonically. New evolution package initializer stays minimal. Keep raw target/destination references, exact dict/str fallbacks, validation order/messages, strict truthiness and broad-scope evidence_count int behavior. Full sanitization, candidate export and actual lifecycle remain legacy.

UpdateVersionSelectionPolicy composes concrete ResourceVersionPolicy and UpdateSitePolicy. Preserve both manifest shapes, borrowing of nested notes/post_update_doctor/update_policy, shared subject mapping per manifest subject, version sorting and warning dedup/order. UpdateAssessmentRenderer preserves the existing rendered bytes and nested formatting helper. No new update/release/network behavior.

## Callers, assurance and delivery

Primary alone integrates every moved Name reference in tools/processforge.py and the one exact external consumer in tools/pf_runtime/mcp_server.py. MCP import must be lazy inside registered_driver_ref after its existing safe_id guard, because standalone transport bootstraps src later. Instantiate RuntimeDriverCatalogReader(core.ROOT) using only that root value; retain bound_project/workplace/error mapping/resolve and all existing action schemas. No obsolete wrappers/aliases. Primary owns EN/RU ownership docs and exact changed/new checksum rows; preserve known unrelated drift.

Before writers, capture exact source/AST/constants. Contributors use small compile/AST checks only. Primary runs bounded old/new comparison, direct/copied Core and focused driver I/O fixtures in its own allowed scratch, then only affected existing authoring/import/parity/candidate/update/driver/MCP smokes. No permanent tests, fixture retries in native workers, blanket release suites, ZIP-content, archive/install/host qualification or infrastructure action. Reuse successful receipts unless a new change/failure justifies a scoped repeat. Reviewer inspects actual frozen source/evidence independently and pins final hashes; changes after review need focused re-review.

After accepted review, commit explicit paths only, preserve unrelated changes/index, push identical SHA to origin/dev and gitverse/dev and verify both. GitVerse must use existing GITVERSE_TOKEN in process-only configuration with credential helper disabled. No credentials/private machine paths in public evidence. Finish exact native release/evolve, terminal doctor and architecture reread before another bounded cycle. User cutoff for starting new tasks is 2026-10-19 09:00 device time; finish current tasks afterward and report the night.
