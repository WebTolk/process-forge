# Release Test Report

- result: `FAIL`
- public: `false`
- started_at: `2026-09-07T13:56:22Z`
- finished_at: `2026-09-07T14:11:47Z`
- elapsed_seconds: `924.93`

## Checks

| Check | Layer | Public Gate | Status | Exit | Elapsed | Timeout |
|---|---|---:|---:|---:|---:|---:|
| `py_compile` | `public` | true | PASS | 0 | 4.50s | 30s |
| `schema validation` | `public` | true | PASS | 0 | 18.01s | 60s |
| `public cleanliness` | `public` | true | PASS | 0 | 6.44s | 60s |
| `smoke_public_cleanliness` | `public` | true | PASS | 0 | 0.63s | 60s |
| `smoke_processforge_core_package_bootstrap` | `public` | true | PASS | 0 | 0.70s | 120s |
| `smoke_central_event_ingress` | `public` | true | PASS | 0 | 20.00s | 180s |
| `smoke_core_has_no_domain_knowledge_seeds` | `public` | true | PASS | 0 | 0.11s | 120s |
| `smoke_empty_workplace_has_no_domain_resources` | `public` | true | PASS | 0 | 2.32s | 120s |
| `smoke_project_classification_data_driven` | `public` | true | PASS | 0 | 0.93s | 120s |
| `smoke_project_onboard_platform_selection` | `public` | true | PASS | 0 | 1.09s | 120s |
| `smoke_no_hardcoded_file_project_detection` | `public` | true | PASS | 0 | 0.40s | 120s |
| `smoke_optional_domain_pack_not_default` | `public` | true | PASS | 0 | 0.32s | 120s |
| `smoke_domain_pack_can_classify_after_install` | `public` | true | PASS | 0 | 0.40s | 120s |
| `smoke_core_process_catalog_domain_neutral` | `public` | true | PASS | 0 | 1.13s | 120s |
| `smoke_core_prompts_domain_neutral` | `public` | true | PASS | 0 | 0.09s | 120s |
| `smoke_runtime_no_domain_file_patterns` | `public` | true | PASS | 0 | 0.94s | 120s |
| `smoke_official_packs_not_examples` | `public` | true | PASS | 0 | 0.31s | 120s |
| `smoke_official_pack_manifest_schema` | `public` | true | PASS | 0 | 0.31s | 120s |
| `smoke_official_software_process_available` | `public` | true | PASS | 0 | 12.82s | 120s |
| `smoke_official_pack_not_kernel` | `public` | true | PASS | 0 | 0.75s | 120s |
| `smoke_generic_workplace_no_domain_pack_active` | `public` | true | PASS | 0 | 2.74s | 120s |
| `smoke_software_profile_activates_official_pack` | `public` | true | PASS | 0 | 7.10s | 180s |
| `smoke_official_pack_classifier_data_driven` | `public` | true | PASS | 0 | 13.57s | 180s |
| `smoke_official_process_can_start_minimal_run` | `public` | true | PASS | 0 | 21.74s | 180s |
| `smoke_core_domain_neutral_still_passes` | `public` | true | PASS | 0 | 15.50s | 180s |
| `smoke_examples_do_not_shadow_official_processes` | `public` | true | PASS | 0 | 0.25s | 120s |
| `checksum` | `public` | true | PASS | 0 | 0.37s | 60s |
| `smoke_first_run` | `public` | true | PASS | 0 | 21.88s | 120s |
| `smoke_runtime_driver_registry` | `public` | true | PASS | 0 | 24.57s | 120s |
| `smoke_worker_run_shell` | `public` | true | PASS | 0 | 59.06s | 180s |
| `smoke_worker_environment_secret_redaction` | `public` | true | PASS | 0 | 0.43s | 120s |
| `smoke_worker_workspace_access` | `public` | true | PASS | 0 | 8.51s | 180s |
| `smoke_codex_exec_worker` | `public` | true | PASS | 0 | 8.83s | 180s |
| `smoke_codex_worker_governance` | `public` | true | PASS | 0 | 0.38s | 120s |
| `smoke_mcp_codex_contract` | `public` | true | PASS | 0 | 4.13s | 120s |
| `smoke_runtime_mcp_autostart` | `public` | true | PASS | 0 | 0.21s | 120s |
| `smoke_central_event_replay` | `public` | true | PASS | 0 | 8.28s | 180s |
| `smoke_conversation_completeness` | `public` | true | PASS | 0 | 57.86s | 180s |
| `smoke_process_supervisor_tick` | `public` | true | PASS | 0 | 15.39s | 180s |
| `smoke_director_inspector_boundary` | `public` | true | PASS | 0 | 18.93s | 180s |
| `smoke_process_run_task_batch` | `public` | true | PASS | 0 | 74.89s | 180s |
| `smoke_agent_ledger` | `public` | true | PASS | 0 | 8.70s | 120s |
| `smoke_single_agent_session_flow` | `public` | true | PASS | 0 | 15.56s | 180s |
| `smoke_multi_project_agent_sessions` | `public` | true | PASS | 0 | 11.99s | 180s |
| `smoke_runtime_host_poc` | `public` | true | PASS | 0 | 26.82s | 180s |
| `smoke_long_lived_runtime` | `public` | true | PASS | 0 | 62.78s | 240s |
| `smoke_multi_agent_as_composed_sessions` | `public` | true | PASS | 0 | 20.61s | 180s |
| `smoke_project_coordination_modes` | `public` | true | PASS | 0 | 14.84s | 180s |
| `smoke_mixed_workplace_projects` | `public` | true | PASS | 0 | 8.97s | 180s |
| `smoke_worker_awareness_of_director` | `public` | true | PASS | 0 | 8.16s | 180s |
| `smoke_error_workflow` | `public` | true | PASS | 0 | 7.35s | 180s |
| `smoke_process_transition_handoff` | `public` | true | PASS | 0 | 9.32s | 120s |
| `smoke_agent_director_tick` | `public` | true | PASS | 0 | 7.45s | 120s |
| `smoke_config_behavior_contracts` | `public` | true | PASS | 0 | 69.03s | 180s |
| `smoke_orchestrator_shell_agents_with_subagent_policy` | `public` | true | PASS | 0 | 20.76s | 180s |
| `smoke_builtin_process_catalog` | `public` | true | PASS | 0 | 3.64s | 120s |
| `smoke_process_directory_layout` | `public` | true | PASS | 0 | 1.19s | 120s |
| `smoke_process_resolver_multiple_roots` | `public` | true | PASS | 0 | 1.83s | 120s |
| `smoke_process_list_origin_filters` | `public` | true | PASS | 0 | 3.89s | 120s |
| `smoke_process_authoring_writes_user_root` | `public` | true | PASS | 0 | 2.20s | 120s |
| `smoke_legacy_flat_process_layout_warning` | `public` | true | PASS | 0 | 1.04s | 120s |
| `smoke_release_pack_excludes_user_processes` | `public` | true | PASS | 0 | 0.25s | 120s |
| `smoke_process_id_stable_after_move` | `public` | true | PASS | 0 | 0.88s | 120s |
| `smoke_process_root_collision_policy` | `public` | true | PASS | 0 | 0.82s | 120s |
| `smoke_project_scan_excludes_distribution_root` | `public` | true | PASS | 0 | 0.27s | 120s |
| `smoke_project_scan_excludes_workplace_root` | `public` | true | PASS | 0 | 0.33s | 120s |
| `smoke_project_scan_excludes_knowledge_roots` | `public` | true | PASS | 0 | 0.28s | 120s |
| `smoke_processforge_core_project_requires_explicit_type` | `public` | true | PASS | 0 | 0.33s | 120s |
| `smoke_project_local_package_index_detection` | `public` | true | PASS | 0 | 0.42s | 120s |
| `smoke_agent_workspace_platform_availability_snapshot` | `public` | true | PASS | 0 | 0.60s | 120s |
| `smoke_platform_create_include_levels` | `public` | true | PASS | 0 | 1.83s | 120s |
| `smoke_release_test_trace_timeout_reporting` | `public` | true | PASS | 0 | 1.48s | 120s |
| `smoke_release_test_extracted_archive` | `public` | true | PASS | 0 | 0.25s | 120s |
| `smoke_windows_utf8_docs` | `public` | true | PASS | 0 | 0.10s | 120s |
| `smoke_pf_project_process_refs_follow_layout` | `public` | true | PASS | 0 | 0.30s | 120s |
| `smoke_no_removed_process_refs` | `public` | true | PASS | 0 | 0.24s | 120s |
| `smoke_update_sites_schema` | `public` | true | PASS | 0 | 2.52s | 120s |
| `smoke_update_candidate_discovery` | `public` | true | PASS | 0 | 2.47s | 120s |
| `smoke_update_notifications` | `public` | true | PASS | 0 | 3.25s | 120s |
| `smoke_update_stage_verify_apply_file_provider` | `public` | true | PASS | 0 | 4.87s | 120s |
| `smoke_core_update_manifest` | `public` | true | PASS | 0 | 5.44s | 120s |
| `smoke_project_pf_upgrade_assessment_boundary` | `public` | true | PASS | 0 | 19.30s | 120s |
| `smoke_tool_update_policy` | `public` | true | PASS | 0 | 3.24s | 120s |
| `smoke_resource_versioning_modes` | `public` | true | PASS | 0 | 4.03s | 120s |
| `smoke_project_context_snapshot_lock_model` | `public` | true | PASS | 0 | 2.32s | 120s |
| `smoke_project_context_freshness_policies` | `public` | true | PASS | 0 | 5.12s | 120s |
| `smoke_context_freshness_vs_execution_readiness` | `public` | true | PASS | 0 | 19.03s | 180s |
| `smoke_process_catalog_not_implicit_execution_route` | `public` | true | PASS | 0 | 12.05s | 180s |
| `smoke_project_init_local_search_mcp` | `public` | true | PASS | 0 | 28.15s | 180s |
| `smoke_resource_indexing_policy_acceptance` | `public` | true | PASS | 0 | 0.38s | 180s |
| `smoke_project_init_acceptance` | `public` | true | PASS | 0 | 37.05s | 180s |
| `smoke_project_init_codex_integration` | `public` | true | PASS | 0 | 8.62s | 180s |
| `smoke_no_production_example_update_urls` | `public` | true | PASS | 0 | 0.12s | 120s |
| `smoke_docs_garage_no_runtime_required` | `public` | true | PASS | 0 | 0.10s | 120s |
| `smoke_docs_mcp_host_owned_stdio` | `public` | true | PASS | 0 | 0.12s | 120s |
| `smoke_docs_agent_no_manual_infra` | `public` | true | PASS | 0 | 0.13s | 120s |
| `smoke_docs_current_code_contract` | `public` | true | PASS | 0 | 0.63s | 120s |
| `smoke_docs_codex_hooks_optional` | `public` | true | PASS | 0 | 0.10s | 120s |
| `smoke_doctor_gitignore_effective_protection` | `public` | true | PASS | 0 | 4.20s | 180s |
| `smoke_mcp_missing_session_diagnostics` | `public` | true | PASS | 0 | 0.19s | 120s |
| `smoke_session_projection_expiry` | `public` | true | PASS | 0 | 4.28s | 180s |
| `smoke_fulltext_article_indexing` | `public` | true | PASS | 0 | 0.23s | 120s |
| `smoke_garage_no_hooks_sessionless` | `public` | true | FAIL | 1 | 5.62s | 180s |
