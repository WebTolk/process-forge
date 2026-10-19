"""Build workplace setup proposals with the existing proposal and Markdown contract."""

from __future__ import annotations

from typing import Any

from ..common.ids import safe_id
from ..common.values import as_list
from .coordination import ProjectCoordinationReader


class WorkplaceSetupProposalBuilder:
    """Construct the existing review proposal without applying workplace changes."""

    def __init__(self) -> None:
        self.coordination = ProjectCoordinationReader()

    def build(self, session_id: str, answers: dict[str, Any]) -> tuple[dict[str, Any], str]:
        machine = answers.get("machine_layout") if isinstance(answers.get("machine_layout"), dict) else {}
        agents = answers.get("agent_environment") if isinstance(answers.get("agent_environment"), dict) else {}
        discovery = answers.get("device_discovery") if isinstance(answers.get("device_discovery"), dict) else {}
        resources = answers.get("resources") if isinstance(answers.get("resources"), dict) else {}
        first_project = answers.get("first_project") if isinstance(answers.get("first_project"), dict) else {}
        coordination = answers.get("coordination") if isinstance(answers.get("coordination"), dict) else {}
        proposal = {
            "schema_version": 1,
            "session_id": safe_id(session_id, "setup-session"),
            "status": "ready_for_review",
            "workplace": {"path_ref": str(machine.get("workplace_path") or "${PF_WORKPLACE}")},
            "processforge": {"root_ref": str(machine.get("processforge_root") or "${PROCESSFORGE_ROOT}")},
            "local_docs": {"path_ref": str(machine.get("local_docs_path") or "${PF_WORKPLACE}/knowledge")},
            "project_roots": [str(item) for item in as_list(machine.get("project_roots"))],
            "agent_environments": [str(item) for item in as_list(agents.get("tools") or ["generic"])],
            "instruction_targets": [str(item) for item in as_list(agents.get("instructions_targets") or ["AGENTS.md"])],
            "device_discovery": {
                "enabled": str(discovery.get("enabled") or "ask"),
                "read_only": bool(discovery.get("read_only", True)),
                "outputs": [
                    str(item)
                    for item in as_list(
                        discovery.get("outputs")
                        or ["device-discovery-report.md", "resource-candidates.yaml", "auto-setup-proposal.md"]
                    )
                ],
            },
            "registries": {
                "knowledge_roots": resources.get("knowledge_roots", []),
                "package_roots": resources.get("package_roots", []),
                "tools": resources.get("tools", []),
                "mcp_servers": resources.get("mcp_servers", []),
                "templates": resources.get("templates", []),
            },
            "privacy": answers.get("privacy_safety", {}),
            "platform_policy": answers.get("platform_contracts", {}),
            "coordination": {
                "director_capability": bool(coordination.get("director_capability", False)),
                "default_project_mode": self.coordination.workplace_mode(coordination.get("default_project_mode", "simple")),
                "initialize_director_office": bool(coordination.get("initialize_director_office", False)),
            },
            "first_project": first_project,
            "apply_steps": [
                "review optional device-discovery findings and resource candidates",
                "run workplace-init internals",
                "write workplace registries",
                "write agent instruction snippet",
                "run doctor-workplace",
                "write project-onboard next steps",
            ],
        }
        md = f"""# Guided Workplace Setup Proposal

## Session

- id: `{safe_id(session_id, "setup-session")}`
- status: `ready_for_review`

## Layout

- ProcessForge root: `{proposal["processforge"]["root_ref"]}`
- Workplace: `{proposal["workplace"]["path_ref"]}`
- Local docs: `{proposal["local_docs"]["path_ref"]}`
- Project roots: {", ".join(proposal["project_roots"]) if proposal["project_roots"] else "not set"}
- Director capability: {str(proposal["coordination"]["director_capability"]).lower()}
- Default project mode: {proposal["coordination"]["default_project_mode"]}
- Initialize Director Office: {str(proposal["coordination"]["initialize_director_office"]).lower()}

## Agent Environments

- Tools: {", ".join(proposal["agent_environments"])}
- Instruction targets: {", ".join(proposal["instruction_targets"])}

## Device Discovery

- Enabled: {proposal["device_discovery"]["enabled"]}
- Read only: {str(proposal["device_discovery"]["read_only"]).lower()}
- Outputs: {", ".join(proposal["device_discovery"]["outputs"])}

## Apply Plan

1. Review optional device-discovery findings and resource candidates.
2. Create or update the workplace layer through `workplace-init`.
3. Preserve private machine paths inside workplace-local files.
4. Generate a bounded ProcessForge agent instruction snippet.
5. Run `doctor-workplace`.
6. Write project onboarding next steps.
"""
        return proposal, md
