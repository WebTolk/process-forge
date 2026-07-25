# Public Core Migration Map

| Previous path | New path or owner | Reason |
|---|---|---|
| `.pf/artifacts/checksum-inventory.sha256` | `checksums/processforge.sha256` | Product checksum must be archived without publishing `.pf/artifacts/`. |
| `tools/smoke_resource_management.py` | `.pf/dogfooding/tests/scripts/smoke_resource_management.py` | Internal resource-management regression. |
| `tools/smoke_resource_authoring_processes.py` | `.pf/dogfooding/tests/scripts/smoke_resource_authoring_processes.py` | Internal authoring-chain regression. |
| `tools/smoke_update_framework_readonly.py` | `.pf/dogfooding/tests/scripts/smoke_update_framework_readonly.py` | Internal update-framework regression. |
| `tools/smoke_update_framework_validation.py` | `.pf/dogfooding/tests/scripts/smoke_update_framework_validation.py` | Internal update-framework regression. |
| `tools/smoke_guided_workplace_setup.py` | `.pf/dogfooding/tests/scripts/smoke_guided_workplace_setup.py` | Internal setup workflow regression. |
| `tools/smoke_multiagent_orchestration_process.py` | `.pf/dogfooding/tests/scripts/smoke_multiagent_orchestration_process.py` | Internal multi-agent workflow regression. |
| `tools/smoke_multiagent_assignment_contract.py` | `.pf/dogfooding/tests/scripts/smoke_multiagent_assignment_contract.py` | Internal assignment contract regression. |
| `tools/smoke_worker_run_manual.py` | `.pf/dogfooding/tests/scripts/smoke_worker_run_manual.py` | Internal worker lifecycle regression. |
| `tools/smoke_worker_run_lifecycle.py` | `.pf/dogfooding/tests/scripts/smoke_worker_run_lifecycle.py` | Internal worker lifecycle regression. |
| `tools/smoke_supervisor_final_drain.py` | `.pf/dogfooding/tests/scripts/smoke_supervisor_final_drain.py` | Internal detached-state regression. |
| `tools/smoke_process_supervisor_lifecycle.py` | `.pf/dogfooding/tests/scripts/smoke_process_supervisor_lifecycle.py` | Internal supervisor lifecycle regression. |
| `tools/smoke_process_supervisor.py` | `.pf/dogfooding/tests/scripts/smoke_process_supervisor.py` | Internal supervisor chain regression. |
| `tools/smoke_shell_launched_agents_supervisor_fix.py` | `.pf/dogfooding/tests/scripts/smoke_shell_launched_agents_supervisor_fix.py` | Internal shell-agent fix regression. |
| `tools/smoke_shell_agent_heartbeat_contract.py` | `.pf/dogfooding/tests/scripts/smoke_shell_agent_heartbeat_contract.py` | Internal heartbeat contract regression. |
| `tools/smoke_full_shell_agents_supervisor.py` | `.pf/dogfooding/tests/scripts/smoke_full_shell_agents_supervisor.py` | Internal full shell-agent stress regression. |
| `tools/smoke_manifest_driven_platforms.py` | `.pf/dogfooding/tests/scripts/smoke_manifest_driven_platforms.py` | Internal platform policy regression. |
| `tools/smoke_platform_inheritance.py` | `.pf/dogfooding/tests/scripts/smoke_platform_inheritance.py` | Internal inheritance regression. |
| `tools/smoke_process_authoring.py` | `.pf/dogfooding/tests/scripts/smoke_process_authoring.py` | Internal authoring regression. |
| `tools/smoke_authoring_parity.py` | `.pf/dogfooding/tests/scripts/smoke_authoring_parity.py` | Internal parity regression. |
