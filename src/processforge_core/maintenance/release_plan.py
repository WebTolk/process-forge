"""Ordered construction of the existing release-validation command plan."""

from __future__ import annotations

import sys
from pathlib import Path

from processforge_core.common.properties import CoreProperties
from processforge_core.common.release_identity import RELEASE_NAME
from processforge_core.maintenance.release_commands import ReleaseCommand


class ReleaseCommandPlanBuilder:
    def release_test_commands(
        self, root: Path, *, clean_first: bool = True, public: bool = False
    ) -> list[ReleaseCommand]:
        commands: list[ReleaseCommand] = [
            ReleaseCommand(
                "py_compile",
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(root / "tools" / "processforge.py"),
                    str(root / "bin" / "pf.py"),
                    str(root / "tools" / "specialization_smoke_helpers.py"),
                    str(root / "tools" / "codex_exec_worker.py"),
                ],
                30,
            ),
            ReleaseCommand(
                "smoke_cli_audit_f0608",
                [sys.executable, str(root / "tools" / "smoke_cli_audit_f0608.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_core_update_missing_owned",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_update_missing_owned.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_search_source_integrity",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_search_source_integrity.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_search_file_root_containment",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_search_file_root_containment.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_search_multiple_roots",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_search_multiple_roots.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_classifier_distribution_parity",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_classifier_distribution_parity.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_scheduler_failure_isolation",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_runtime_scheduler_failure_isolation.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_singleton_orphan",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_runtime_singleton_orphan.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_core_update_migration_sources",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_update_migration_sources.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_expected_report_containment",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_expected_report_containment.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_authenticated_report_content",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_authenticated_report_content.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_mcp_jsonrpc_validation",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_mcp_jsonrpc_validation.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_action_discovery",
                [sys.executable, str(root / "tools" / "smoke_action_discovery.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_mcp_action_tools",
                [sys.executable, str(root / "tools" / "smoke_mcp_action_tools.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_mcp_stdio_unicode",
                [sys.executable, str(root / "tools" / "smoke_mcp_stdio_unicode.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_diagnostics",
                [sys.executable, str(root / "tools" / "smoke_diagnostics.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_diagnostics_process_invariance",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_diagnostics_process_invariance.py"),
                ],
                240,
            ),
            ReleaseCommand(
                "smoke_work_resource_binding",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_resource_binding.py"),
                ],
                300,
            ),
            ReleaseCommand(
                "smoke_work_capsule_contract_parity",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_capsule_contract_parity.py"),
                ],
                300,
            ),
            ReleaseCommand(
                "smoke_session_identity_roundtrip",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_session_identity_roundtrip.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_codex_lifecycle_identity",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_codex_lifecycle_identity.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_raw_ingress_incremental_recovery",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_raw_ingress_incremental_recovery.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "schema validation",
                [
                    sys.executable,
                    str(root / "tools" / "validate-process-forge-schemas.py"),
                    "--root",
                    str(root),
                ],
                60,
            ),
            ReleaseCommand(
                "public cleanliness",
                [
                    sys.executable,
                    str(root / "tools" / "validate-public-cleanliness.py"),
                    "--root",
                    str(root),
                ],
                60,
            ),
            ReleaseCommand(
                "smoke_public_cleanliness",
                [sys.executable, str(root / "tools" / "smoke_public_cleanliness.py")],
                60,
            ),
            ReleaseCommand(
                "smoke_processforge_core_package_bootstrap",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_processforge_core_package_bootstrap.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_yaml_inventory",
                [sys.executable, str(root / "tools" / "smoke_yaml_inventory.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_core_read_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_read_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_core_work_state",
                [sys.executable, str(root / "tools" / "smoke_core_work_state.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_work_record_read_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_record_read_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_work_context_read_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_context_read_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_definition_read_composition",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_process_definition_read_composition.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_snapshot_read_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_snapshot_read_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_garage_snapshot_read_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_snapshot_read_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_resource_search_snapshot_composition",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_resource_search_snapshot_composition.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_resource_resolve_snapshot_composition",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_resource_resolve_snapshot_composition.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_garage_mode_snapshot_composition",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_mode_snapshot_composition.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_evidence_collection_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evidence_collection_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_evidence_validation_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evidence_validation_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_automation_readiness",
                [sys.executable, str(root / "tools" / "smoke_automation_readiness.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_work_selection_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_selection_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_selection_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_selection_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_pin_read_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_pin_read_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_run_completion_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_run_completion_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_completion_intent_validation_service",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_completion_intent_validation_service.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_transition_rejection_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_transition_rejection_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_work_boundary_advisory_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_boundary_advisory_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_completion_document_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_completion_document_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_completion_intent_builder",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_completion_intent_builder.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_completion_intent_read_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_completion_intent_read_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_completion_intent_replay_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_completion_intent_replay_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_work_transition_commit_service",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_transition_commit_service.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_stage_readiness_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_stage_readiness_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_subprocess_capture",
                [sys.executable, str(root / "tools" / "smoke_subprocess_capture.py")],
                60,
            ),
            ReleaseCommand(
                "smoke_central_event_ingress",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_central_event_ingress.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_provider_adapter_admission",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_provider_adapter_admission.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_prepared_execution_context",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_prepared_execution_context.py"),
                ],
                360,
            ),
            ReleaseCommand(
                "smoke_prepared_execution_recovery",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_prepared_execution_recovery.py"),
                ],
                240,
            ),
            ReleaseCommand(
                "smoke_core_has_no_domain_knowledge_seeds",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_has_no_domain_knowledge_seeds.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_empty_workplace_has_no_domain_resources",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_empty_workplace_has_no_domain_resources.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_classification_data_driven",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_classification_data_driven.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_classifier_inventory_pruning",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_classifier_inventory_pruning.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_onboard_platform_selection",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_onboard_platform_selection.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_no_hardcoded_file_project_detection",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_no_hardcoded_file_project_detection.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_optional_domain_pack_not_default",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_optional_domain_pack_not_default.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_domain_pack_can_classify_after_install",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_domain_pack_can_classify_after_install.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_core_process_catalog_domain_neutral",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_core_process_catalog_domain_neutral.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_core_prompts_domain_neutral",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_prompts_domain_neutral.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_no_domain_file_patterns",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_runtime_no_domain_file_patterns.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_official_packs_not_examples",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_official_packs_not_examples.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_official_pack_manifest_schema",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_official_pack_manifest_schema.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_official_software_process_available",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_official_software_process_available.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_official_pack_not_kernel",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_official_pack_not_kernel.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_generic_workplace_no_domain_pack_active",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_generic_workplace_no_domain_pack_active.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_profile_activates_official_pack",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_software_profile_activates_official_pack.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_official_pack_classifier_data_driven",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_official_pack_classifier_data_driven.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_official_process_can_start_minimal_run",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_official_process_can_start_minimal_run.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_core_domain_neutral_still_passes",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_core_domain_neutral_still_passes.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_examples_do_not_shadow_official_processes",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_examples_do_not_shadow_official_processes.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "checksum",
                [
                    sys.executable,
                    str(root / "tools" / "validate-process-forge-checksums.py"),
                    "--root",
                    str(root),
                    "--check",
                ],
                60,
            ),
            ReleaseCommand(
                "smoke_first_run",
                [sys.executable, str(root / "tools" / "smoke_first_run.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_driver_registry",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_runtime_driver_registry.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_worker_run_shell",
                [sys.executable, str(root / "tools" / "smoke_worker_run_shell.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_worker_environment_secret_redaction",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_worker_environment_secret_redaction.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_worker_workspace_access",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_worker_workspace_access.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_codex_exec_worker",
                [sys.executable, str(root / "tools" / "smoke_codex_exec_worker.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_codex_worker_governance",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_codex_worker_governance.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_mcp_codex_contract",
                [sys.executable, str(root / "tools" / "smoke_mcp_codex_contract.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_mcp_autostart",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_runtime_mcp_autostart.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_central_event_replay",
                [sys.executable, str(root / "tools" / "smoke_central_event_replay.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_conversation_completeness",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_conversation_completeness.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_process_supervisor_tick",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_supervisor_tick.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_director_inspector_boundary",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_director_inspector_boundary.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_process_run_task_batch",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_run_task_batch.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_agent_ledger",
                [sys.executable, str(root / "tools" / "smoke_agent_ledger.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_single_agent_session_flow",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_single_agent_session_flow.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_multi_project_agent_sessions",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_multi_project_agent_sessions.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_runtime_host_poc",
                [sys.executable, str(root / "tools" / "smoke_runtime_host_poc.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_long_lived_runtime",
                [sys.executable, str(root / "tools" / "smoke_long_lived_runtime.py")],
                240,
            ),
            ReleaseCommand(
                "smoke_multi_agent_as_composed_sessions",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_multi_agent_as_composed_sessions.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_project_coordination_modes",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_coordination_modes.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_mixed_workplace_projects",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_mixed_workplace_projects.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_worker_awareness_of_director",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_worker_awareness_of_director.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_error_workflow",
                [sys.executable, str(root / "tools" / "smoke_error_workflow.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_process_transition_handoff",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_transition_handoff.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_agent_director_tick",
                [sys.executable, str(root / "tools" / "smoke_agent_director_tick.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_config_behavior_contracts",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_config_behavior_contracts.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_orchestrator_shell_agents_with_subagent_policy",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_orchestrator_shell_agents_with_subagent_policy.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_builtin_process_catalog",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_builtin_process_catalog.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_directory_layout",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_directory_layout.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_resolver_multiple_roots",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_resolver_multiple_roots.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_list_origin_filters",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_list_origin_filters.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_authoring_writes_user_root",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_authoring_writes_user_root.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_legacy_flat_process_layout_warning",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_legacy_flat_process_layout_warning.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_release_pack_excludes_user_processes",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_release_pack_excludes_user_processes.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_id_stable_after_move",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_id_stable_after_move.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_root_collision_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_root_collision_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_scan_excludes_distribution_root",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_scan_excludes_distribution_root.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_scan_excludes_workplace_root",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_project_scan_excludes_workplace_root.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_scan_excludes_knowledge_roots",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_scan_excludes_knowledge_roots.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_processforge_core_project_requires_explicit_type",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_processforge_core_project_requires_explicit_type.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_local_package_index_detection",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_local_package_index_detection.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_agent_workspace_platform_availability_snapshot",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_agent_workspace_platform_availability_snapshot.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_platform_create_include_levels",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_platform_create_include_levels.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_release_test_trace_timeout_reporting",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_release_test_trace_timeout_reporting.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_release_test_extracted_archive",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_release_test_extracted_archive.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_windows_utf8_docs",
                [sys.executable, str(root / "tools" / "smoke_windows_utf8_docs.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_pf_project_process_refs_follow_layout",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_pf_project_process_refs_follow_layout.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_no_removed_process_refs",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_no_removed_process_refs.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_update_sites_schema",
                [sys.executable, str(root / "tools" / "smoke_update_sites_schema.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_update_candidate_discovery",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_update_candidate_discovery.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_update_notifications",
                [sys.executable, str(root / "tools" / "smoke_update_notifications.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_update_stage_verify_apply_file_provider",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_update_stage_verify_apply_file_provider.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_core_update_manifest",
                [sys.executable, str(root / "tools" / "smoke_core_update_manifest.py")],
                300,
            ),
            ReleaseCommand(
                "smoke_project_pf_upgrade_assessment_boundary",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_pf_upgrade_assessment_boundary.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_tool_update_policy",
                [sys.executable, str(root / "tools" / "smoke_tool_update_policy.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_resource_versioning_modes",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_resource_versioning_modes.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_context_snapshot_lock_model",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_project_context_snapshot_lock_model.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_context_freshness_policies",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_context_freshness_policies.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_context_freshness_vs_execution_readiness",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_context_freshness_vs_execution_readiness.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_project_context_capability_records_real_core",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_context_capability_records_real_core.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_continuation_work",
                [sys.executable, str(root / "tools" / "smoke_continuation_work.py")],
                240,
            ),
            ReleaseCommand(
                "smoke_process_catalog_not_implicit_execution_route",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_process_catalog_not_implicit_execution_route.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_project_init_local_search_mcp",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_init_local_search_mcp.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_resource_indexing_policy_acceptance",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_resource_indexing_policy_acceptance.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_project_init_acceptance",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_init_acceptance.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_project_init_entry",
                [sys.executable, str(root / "tools" / "smoke_project_init_entry.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_agent_entry",
                [sys.executable, str(root / "tools" / "smoke_agent_entry.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_agent_entry_release",
                [sys.executable, str(root / "tools" / "smoke_agent_entry_release.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_agent_start_prompt",
                [sys.executable, str(root / "tools" / "smoke_agent_start_prompt.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_agent_entry_profiles",
                [sys.executable, str(root / "tools" / "smoke_agent_entry_profiles.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_agent_entry_adapters",
                [sys.executable, str(root / "tools" / "smoke_agent_entry_adapters.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_project_init_codex_integration",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_init_codex_integration.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_no_production_example_update_urls",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_no_production_example_update_urls.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_docs_garage_no_runtime_required",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_docs_garage_no_runtime_required.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_docs_mcp_host_owned_stdio",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_docs_mcp_host_owned_stdio.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_docs_agent_no_manual_infra",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_docs_agent_no_manual_infra.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_docs_current_code_contract",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_docs_current_code_contract.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_docs_codex_hooks_optional",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_docs_codex_hooks_optional.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_doctor_gitignore_effective_protection",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_doctor_gitignore_effective_protection.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_mcp_missing_session_diagnostics",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_mcp_missing_session_diagnostics.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_session_projection_expiry",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_session_projection_expiry.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_fulltext_article_indexing",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_fulltext_article_indexing.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_garage_no_hooks_sessionless",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_no_hooks_sessionless.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_session_enhanced",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_session_enhanced.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_cross_project_security",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_cross_project_security.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_real_joomla_search",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_real_joomla_search.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_mode_not_promoted_by_session",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_garage_mode_not_promoted_by_session.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_work_start_sessionless",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_work_start_sessionless.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_garage_work_start_session_bound",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_garage_work_start_session_bound.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_multi_process_work_capsule",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_multi_process_work_capsule.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_governed_work_stage_resolution",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_governed_work_stage_resolution.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_governed_work_duplicate_prevention",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_governed_work_duplicate_prevention.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_current_work_ignores_bootstrap_placeholder",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_current_work_ignores_bootstrap_placeholder.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_process_execution_initial_stage",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_execution_initial_stage.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_start_no_stage_guessing",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_start_no_stage_guessing.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_state_current_stage",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_state_current_stage.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_linear",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_transition_linear.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_blocks_missing_gate",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_work_transition_blocks_missing_gate.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_recovers_after_invalid_evidence",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_work_transition_recovers_after_invalid_evidence.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_records_evidence",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_transition_records_evidence.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_evidence_freshness",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_evidence_freshness.py"),
                ],
                360,
            ),
            ReleaseCommand(
                "smoke_work_completion_recovery",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_completion_recovery.py"),
                ],
                360,
            ),
            ReleaseCommand(
                "smoke_work_transition_updates_assignment_stage",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_work_transition_updates_assignment_stage.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_emits_stage_events",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_work_transition_emits_stage_events.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_final_stage_completes_run",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_work_transition_final_stage_completes_run.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_snapshot_pinned_process",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_work_transition_snapshot_pinned_process.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_work_transition_branching_if_supported",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_work_transition_branching_if_supported.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_process_execution_integrity",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_execution_integrity.py"),
                ],
                240,
            ),
            ReleaseCommand(
                "smoke_derived_report_stale_marking",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_derived_report_stale_marking.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_runtime_status_version_truth",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_runtime_status_version_truth.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_runtime_monitor",
                [sys.executable, str(root / "tools" / "smoke_runtime_monitor.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_metrics",
                [sys.executable, str(root / "tools" / "smoke_runtime_metrics.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_workplace_configuration",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_workplace_configuration.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_server_operator",
                [sys.executable, str(root / "tools" / "smoke_server_operator.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_diagnostics_configure",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_diagnostics_configure.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_event_concurrency",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_event_concurrency.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_user_like_garage_path",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_user_like_garage_path.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_parameter_cascade_resolution",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_parameter_cascade_resolution.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_parameter_freshness",
                [sys.executable, str(root / "tools" / "smoke_parameter_freshness.py")],
                120,
            ),
            ReleaseCommand(
                "smoke_parameter_assignment_capsule",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_parameter_assignment_capsule.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_session_start_context_check",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_session_start_context_check.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_update_apply_marks_context_stale",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_update_apply_marks_context_stale.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_capsule_pins_context_snapshot",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_capsule_pins_context_snapshot.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_no_builtin_user_capability_satisfaction",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_no_builtin_user_capability_satisfaction.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_capability_resolution_data_driven_only",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_capability_resolution_data_driven_only.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_doctor_project_capability_waiver",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_doctor_project_capability_waiver.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_domain_neutral_music_video_fixtures",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_domain_neutral_music_video_fixtures.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_runtime_no_domain_capability_constants",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_runtime_no_domain_capability_constants.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_nested_workflow_fields_rejected",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_specialization_nested_workflow_fields_rejected.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_freshness_tracks_definition_change",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_specialization_freshness_tracks_definition_change.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_specialization_override_applies",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_specialization_override_applies.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_schema",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_schema.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_registry",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_registry.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_create_workplace_resource",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_specialization_create_workplace_resource.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_platform_binding",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_platform_binding.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_context_resolution",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_context_resolution.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_same_platform_different_context",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_specialization_same_platform_different_context.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_no_tool_leakage",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_no_tool_leakage.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_no_workflow_ownership",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_specialization_no_workflow_ownership.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_owns_acceptance_not_specialization",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_process_owns_acceptance_not_specialization.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_capability_requirement_resolution",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_process_capability_requirement_resolution.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_process_policy",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_process_policy.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_handoff_routing",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_handoff_routing.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_garage_mode_switch",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_garage_mode_switch.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_snapshot_fields",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_snapshot_fields.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_capsule_activation",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_capsule_activation.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_specialization_no_core_id_hardcode",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_specialization_no_core_id_hardcode.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_overrides_schema",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_overrides_schema.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_overrides_resolution",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_overrides_resolution.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_overrides_snapshot_fingerprint",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_overrides_snapshot_fingerprint.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_overrides_freshness",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_overrides_freshness.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_overrides_capsule_summary",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_project_overrides_capsule_summary.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_project_override_does_not_mutate_workspace",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_project_override_does_not_mutate_workspace.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_authoring_materialization_parity",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_process_authoring_materialization_parity.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_process_definition_schema_contract",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_definition_schema_contract.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_builtin_process_pack_completeness",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_builtin_process_pack_completeness.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_evolve_process_agnostic_contract",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_process_agnostic_contract.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_authoring_evolve_questions",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_authoring_evolve_questions.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_process_authoring_materializes_evolve",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_process_authoring_materializes_evolve.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_generated_processes_include_evolve",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_generated_processes_include_evolve.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_builtin_processes_explicit_evolve",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_builtin_processes_explicit_evolve.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_authoring_crash_recovery",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_authoring_crash_recovery.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_release_manifest_provenance_contract",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_release_manifest_provenance_contract.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_candidate_schema",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_candidate_schema.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_evolve_candidate_targeting_schema",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_candidate_targeting_schema.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_candidate_narrowest_scope",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_candidate_narrowest_scope.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_candidate_split_guidance",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_candidate_split_guidance.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_workplace_learning_queue",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_workplace_learning_queue.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_candidate_export",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_candidate_export.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_privacy_sanitizer",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_privacy_sanitizer.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_targeting_privacy_sanitizer",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_targeting_privacy_sanitizer.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_knowledge_hub_import",
                [sys.executable, str(root / "tools" / "smoke_knowledge_hub_import.py")],
                180,
            ),
            ReleaseCommand(
                "smoke_knowledge_hub_routes_by_target",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_knowledge_hub_routes_by_target.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_child_platform_not_promoted_to_parent",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_child_platform_not_promoted_to_parent.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_knowledge_package_build_from_candidates",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_knowledge_package_build_from_candidates.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_knowledge_package_release_update_manifest",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_knowledge_package_release_update_manifest.py"
                    ),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_evolve_learning_loop_end_to_end",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_evolve_learning_loop_end_to_end.py"),
                ],
                240,
            ),
            ReleaseCommand(
                "smoke_process_authoring_evolve_targeting",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_process_authoring_evolve_targeting.py"),
                ],
                180,
            ),
            ReleaseCommand(
                "smoke_software_process_uses_common_evolve",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_software_process_uses_common_evolve.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_lifecycle_process_contract",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_software_lifecycle_process_contract.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_lifecycle_artifacts",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_software_lifecycle_artifacts.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_lifecycle_description_alignment",
                [
                    sys.executable,
                    str(
                        root
                        / "tools"
                        / "smoke_software_lifecycle_description_alignment.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_lifecycle_prompt_alignment",
                [
                    sys.executable,
                    str(
                        root / "tools" / "smoke_software_lifecycle_prompt_alignment.py"
                    ),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_delivery_profile_not_process",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_delivery_profile_not_process.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "smoke_software_lifecycle_compact_mode",
                [
                    sys.executable,
                    str(root / "tools" / "smoke_software_lifecycle_compact_mode.py"),
                ],
                120,
            ),
            ReleaseCommand(
                "release-check",
                [
                    sys.executable,
                    str(root / "tools" / "processforge.py"),
                    "release-check",
                    "--root",
                    str(root),
                ],
                60,
            ),
            ReleaseCommand(
                "examples-check",
                [
                    sys.executable,
                    str(root / "tools" / "processforge.py"),
                    "examples-check",
                    "--root",
                    str(root),
                ],
                60,
            ),
            ReleaseCommand(
                "events-validate",
                [
                    sys.executable,
                    str(root / "tools" / "processforge.py"),
                    "events-validate",
                    "--project-root",
                    str(root),
                ],
                60,
            ),
            ReleaseCommand(
                "doctor-project",
                [
                    sys.executable,
                    str(root / "tools" / "processforge.py"),
                    "doctor-project",
                    "--project-root",
                    str(root),
                ],
                60,
            ),
        ]
        if clean_first:
            commands.insert(
                1,
                ReleaseCommand(
                    "clean release artifacts",
                    [
                        sys.executable,
                        str(root / "tools" / "processforge.py"),
                        "clean",
                        "--root",
                        str(root),
                        "--release",
                    ],
                    60,
                ),
            )
            if (root / ".git").exists():
                version = CoreProperties.from_distribution(root).loaded.version
                commands.append(
                    ReleaseCommand(
                        "release package",
                        [
                            sys.executable,
                            str(root / "tools" / "processforge.py"),
                            "release-pack",
                            "--root",
                            str(root),
                            "--output",
                            str(root / "dist" / f"{RELEASE_NAME}-{version}.zip"),
                        ],
                        120,
                    )
                )
        if public:
            commands = [item for item in commands if item.public_gate]
        return commands
