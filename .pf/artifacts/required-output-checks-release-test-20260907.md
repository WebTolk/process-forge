# Release Test Report

- result: `FAIL`
- public: `false`
- started_at: `2026-09-07T12:15:07Z`
- finished_at: `2026-09-07T12:28:43Z`
- elapsed_seconds: `816.38`

## Checks

| Check | Layer | Public Gate | Status | Exit | Elapsed | Timeout |
|---|---|---:|---:|---:|---:|---:|
| `py_compile` | `public` | true | PASS | 0 | 3.82s | 30s |
| `schema validation` | `public` | true | PASS | 0 | 20.09s | 60s |
| `public cleanliness` | `public` | true | PASS | 0 | 8.30s | 60s |
| `smoke_public_cleanliness` | `public` | true | PASS | 0 | 1.02s | 60s |
| `smoke_processforge_core_package_bootstrap` | `public` | true | PASS | 0 | 1.60s | 120s |
| `smoke_central_event_ingress` | `public` | true | PASS | 0 | 29.44s | 180s |
| `smoke_core_has_no_domain_knowledge_seeds` | `public` | true | PASS | 0 | 0.13s | 120s |
| `smoke_empty_workplace_has_no_domain_resources` | `public` | true | PASS | 0 | 1.96s | 120s |
| `smoke_project_classification_data_driven` | `public` | true | PASS | 0 | 0.80s | 120s |
| `smoke_project_onboard_platform_selection` | `public` | true | PASS | 0 | 0.98s | 120s |
| `smoke_no_hardcoded_file_project_detection` | `public` | true | PASS | 0 | 0.44s | 120s |
| `smoke_optional_domain_pack_not_default` | `public` | true | PASS | 0 | 0.39s | 120s |
| `smoke_domain_pack_can_classify_after_install` | `public` | true | PASS | 0 | 0.49s | 120s |
| `smoke_core_process_catalog_domain_neutral` | `public` | true | PASS | 0 | 1.48s | 120s |
| `smoke_core_prompts_domain_neutral` | `public` | true | PASS | 0 | 0.15s | 120s |
| `smoke_runtime_no_domain_file_patterns` | `public` | true | PASS | 0 | 1.15s | 120s |
| `smoke_official_packs_not_examples` | `public` | true | PASS | 0 | 0.42s | 120s |
| `smoke_official_pack_manifest_schema` | `public` | true | PASS | 0 | 0.47s | 120s |
| `smoke_official_software_process_available` | `public` | true | PASS | 0 | 10.40s | 120s |
| `smoke_official_pack_not_kernel` | `public` | true | PASS | 0 | 1.26s | 120s |
| `smoke_generic_workplace_no_domain_pack_active` | `public` | true | PASS | 0 | 4.73s | 120s |
| `smoke_software_profile_activates_official_pack` | `public` | true | PASS | 0 | 11.07s | 180s |
| `smoke_official_pack_classifier_data_driven` | `public` | true | PASS | 0 | 13.63s | 180s |
| `smoke_official_process_can_start_minimal_run` | `public` | true | PASS | 0 | 28.25s | 180s |
| `smoke_core_domain_neutral_still_passes` | `public` | true | PASS | 0 | 22.23s | 180s |
| `smoke_examples_do_not_shadow_official_processes` | `public` | true | PASS | 0 | 0.44s | 120s |
| `checksum` | `public` | true | PASS | 0 | 0.82s | 60s |
| `smoke_first_run` | `public` | true | PASS | 0 | 17.53s | 120s |
| `smoke_runtime_driver_registry` | `public` | true | PASS | 0 | 16.72s | 120s |
| `smoke_worker_run_shell` | `public` | true | PASS | 0 | 54.15s | 180s |
| `smoke_worker_environment_secret_redaction` | `public` | true | PASS | 0 | 0.25s | 120s |
| `smoke_worker_workspace_access` | `public` | true | PASS | 0 | 5.06s | 180s |
| `smoke_codex_exec_worker` | `public` | true | PASS | 0 | 5.40s | 180s |
| `smoke_codex_worker_governance` | `public` | true | PASS | 0 | 0.30s | 120s |
| `smoke_mcp_codex_contract` | `public` | true | PASS | 0 | 4.86s | 120s |
| `smoke_runtime_mcp_autostart` | `public` | true | PASS | 0 | 0.38s | 120s |
| `smoke_central_event_replay` | `public` | true | PASS | 0 | 9.40s | 180s |
| `smoke_conversation_completeness` | `public` | true | PASS | 0 | 61.59s | 180s |
| `smoke_process_supervisor_tick` | `public` | true | PASS | 0 | 13.55s | 180s |
| `smoke_director_inspector_boundary` | `public` | true | PASS | 0 | 16.55s | 180s |
| `smoke_process_run_task_batch` | `public` | true | PASS | 0 | 64.09s | 180s |
| `smoke_agent_ledger` | `public` | true | PASS | 0 | 8.30s | 120s |
| `smoke_single_agent_session_flow` | `public` | true | PASS | 0 | 14.19s | 180s |
| `smoke_multi_project_agent_sessions` | `public` | true | PASS | 0 | 15.38s | 180s |
| `smoke_runtime_host_poc` | `public` | true | PASS | 0 | 28.62s | 180s |
| `smoke_long_lived_runtime` | `public` | true | PASS | 0 | 62.21s | 240s |
| `smoke_multi_agent_as_composed_sessions` | `public` | true | PASS | 0 | 18.85s | 180s |
| `smoke_project_coordination_modes` | `public` | true | PASS | 0 | 14.23s | 180s |
| `smoke_mixed_workplace_projects` | `public` | true | PASS | 0 | 9.60s | 180s |
| `smoke_worker_awareness_of_director` | `public` | true | PASS | 0 | 11.45s | 180s |
| `smoke_error_workflow` | `public` | true | PASS | 0 | 11.43s | 180s |
| `smoke_process_transition_handoff` | `public` | true | PASS | 0 | 12.87s | 120s |
| `smoke_agent_director_tick` | `public` | true | PASS | 0 | 10.25s | 120s |
| `smoke_config_behavior_contracts` | `public` | true | PASS | 0 | 62.92s | 180s |
| `smoke_orchestrator_shell_agents_with_subagent_policy` | `public` | true | PASS | 0 | 15.76s | 180s |
| `smoke_builtin_process_catalog` | `public` | true | PASS | 0 | 2.61s | 120s |
| `smoke_process_directory_layout` | `public` | true | PASS | 0 | 0.84s | 120s |
| `smoke_process_resolver_multiple_roots` | `public` | true | PASS | 0 | 1.32s | 120s |
| `smoke_process_list_origin_filters` | `public` | true | PASS | 0 | 2.92s | 120s |
| `smoke_process_authoring_writes_user_root` | `public` | true | PASS | 0 | 1.88s | 120s |
| `smoke_legacy_flat_process_layout_warning` | `public` | true | PASS | 0 | 1.19s | 120s |
| `smoke_release_pack_excludes_user_processes` | `public` | true | PASS | 0 | 0.27s | 120s |
| `smoke_process_id_stable_after_move` | `public` | true | PASS | 0 | 1.26s | 120s |
| `smoke_process_root_collision_policy` | `public` | true | PASS | 0 | 1.19s | 120s |
| `smoke_project_scan_excludes_distribution_root` | `public` | true | PASS | 0 | 0.34s | 120s |
| `smoke_project_scan_excludes_workplace_root` | `public` | true | PASS | 0 | 0.37s | 120s |
| `smoke_project_scan_excludes_knowledge_roots` | `public` | true | PASS | 0 | 0.33s | 120s |
| `smoke_processforge_core_project_requires_explicit_type` | `public` | true | PASS | 0 | 0.41s | 120s |
| `smoke_project_local_package_index_detection` | `public` | true | PASS | 0 | 0.56s | 120s |
| `smoke_agent_workspace_platform_availability_snapshot` | `public` | true | PASS | 0 | 0.69s | 120s |
| `smoke_platform_create_include_levels` | `public` | true | PASS | 0 | 1.87s | 120s |
| `smoke_release_test_trace_timeout_reporting` | `public` | true | PASS | 0 | 1.51s | 120s |
| `smoke_release_test_extracted_archive` | `public` | true | PASS | 0 | 0.22s | 120s |
| `smoke_windows_utf8_docs` | `public` | true | PASS | 0 | 0.08s | 120s |
| `smoke_pf_project_process_refs_follow_layout` | `public` | true | PASS | 0 | 0.35s | 120s |
| `smoke_no_removed_process_refs` | `public` | true | PASS | 0 | 0.19s | 120s |
| `smoke_update_sites_schema` | `public` | true | PASS | 0 | 2.41s | 120s |
| `smoke_update_candidate_discovery` | `public` | true | PASS | 0 | 2.48s | 120s |
| `smoke_update_notifications` | `public` | true | PASS | 0 | 3.18s | 120s |
| `smoke_update_stage_verify_apply_file_provider` | `public` | true | PASS | 0 | 4.94s | 120s |
| `smoke_core_update_manifest` | `public` | true | PASS | 0 | 5.35s | 120s |
| `smoke_project_pf_upgrade_assessment_boundary` | `public` | true | PASS | 0 | 20.68s | 120s |
| `smoke_tool_update_policy` | `public` | true | PASS | 0 | 4.26s | 120s |
| `smoke_resource_versioning_modes` | `public` | true | PASS | 0 | 3.97s | 120s |
| `smoke_project_context_snapshot_lock_model` | `public` | true | PASS | 0 | 2.23s | 120s |
| `smoke_project_context_freshness_policies` | `public` | true | PASS | 0 | 5.19s | 120s |
| `smoke_context_freshness_vs_execution_readiness` | `public` | true | FAIL | 1 | 9.40s | 180s |
