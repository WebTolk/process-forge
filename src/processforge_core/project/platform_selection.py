"""Select existing project platforms and report registry requirements."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.values import list_value, registry_ids
from ..common.yaml_io import _parse_simple_yaml
from ..documents.answers import AnswersDocumentReader
from ..documents.reader import YamlDocumentReader
from ..resources.project_packages import ProjectPackageCatalogReader
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .classification import hint_matches
from .detection import ProjectDetectionService
from .platform_policy import PlatformContractPolicy
from .platforms import PlatformContractReader


class ProjectPlatformSelectionService:
    """Coordinate concrete Core readers without retaining project document state."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.contracts = PlatformContractReader(distribution_root)
        self.contract_policy = PlatformContractPolicy(self.contracts)
        self.detection = ProjectDetectionService()
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.answers = AnswersDocumentReader()
        self.documents = YamlDocumentReader(_parse_simple_yaml)

    def _references(self, workplace_manifest: Path | None, project_root: Path | None = None) -> WorkspacePathReferenceReader:
        return WorkspacePathReferenceReader(
            project_root or (workplace_manifest.parent if workplace_manifest else self.distribution_root),
            workplace_manifest.parent if workplace_manifest else None,
            workplace_manifest=workplace_manifest,
            inputs=ContextContractInputs(documents=self.documents),
        )

    def selected(self, detected: dict[str, Any], answers: dict[str, Any], project_type: str, workplace_manifest: Path | None, project_root: Path) -> list[str]:
        project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
        selected = set(str(item) for item in detected.get("platforms", []) if item)
        for key in ["platform", "platforms", "platform_contract", "platform_contracts"]:
            value = project_answers.get(key)
            if value:
                selected.update(self.contracts.contract_id(item).removeprefix("platform.") for item in self.answers.strings(value))
        selected.update(self.detected_ids(workplace_manifest, project_root))
        selected.update(self.ids_for_project_type(workplace_manifest, project_type, project_root))
        return sorted(selected)

    def project_type_hints(self, contract: dict[str, Any]) -> list[str]:
        hints = list_value(contract.get("project_type_hints"))
        applies_to = contract.get("applies_to") if isinstance(contract.get("applies_to"), dict) else {}
        detection = contract.get("detection") if isinstance(contract.get("detection"), dict) else {}
        hints.extend(list_value(applies_to.get("project_type_hints")))
        hints.extend(list_value(applies_to.get("project_types")))
        hints.extend(list_value(detection.get("project_type_hints")))
        return sorted(set(str(item) for item in hints if item))

    def parent_type_hints(
        self,
        contract: dict[str, Any],
        contracts: dict[str, dict[str, Any]],
        visited: set[str] | None = None,
    ) -> list[str]:
        """Return project type hints declared by a contract's parent graph."""
        seen = set() if visited is None else set(visited)
        hints: set[str] = set()
        parent_refs = [*self.contract_policy.extends(contract), *self.contract_policy.required_platforms(contract)]
        for ref in parent_refs:
            parent_id = ref["id"]
            if parent_id in seen:
                continue
            seen.add(parent_id)
            parent_entry = contracts.get(parent_id)
            if not isinstance(parent_entry, dict):
                continue
            parent_contract = parent_entry.get("contract")
            if not isinstance(parent_contract, dict):
                continue
            hints.update(self.project_type_hints(parent_contract))
            hints.update(self.parent_type_hints(parent_contract, contracts, seen))
        return sorted(hints)

    def ids_for_project_type(self, workplace_manifest: Path | None, project_type: str, project_root: Path | None = None) -> list[str]:
        """Return contracts selected by project type without promoting descendants.

    A derived contract may declare a specific project type, which is valid
    selection evidence. A type hint inherited from its parent, however, makes
    it only a candidate: select it through explicit input, project-classifier
    evidence, or its own concrete detection rules.
    """
        matched: list[str] = []
        contracts = self.contracts.index(workplace_manifest, project_root)
        for contract_id, entry in contracts.items():
            contract = entry["contract"]
            parent_hints = self.parent_type_hints(contract, contracts)
            if parent_hints and hint_matches(project_type, parent_hints):
                continue
            if hint_matches(project_type, self.project_type_hints(contract)):
                matched.append(contract_id.removeprefix("platform."))
        return sorted(set(item for item in matched if item))

    def detected_ids(self, workplace_manifest: Path | None, project_root: Path) -> list[str]:
        matched: list[str] = []
        for contract_id, entry in self.contracts.index(workplace_manifest, project_root).items():
            if self.detection.matches(entry["contract"], project_root):
                matched.append(contract_id.removeprefix("platform."))
        return sorted(set(matched))

    def resource_findings(self, workplace_manifest: Path | None, resolved: dict[str, Any], package_index_ids: set[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        package_ids = registry_ids(self._references(workplace_manifest).load_workplace_registry(workplace_manifest, "package_roots", "package-roots.yaml"), "package_roots")
        if workplace_manifest and workplace_manifest.is_file():
            package_ids = package_ids.union(set(self.packages.index(workplace_manifest.parent, None, workplace_manifest)) - {"__duplicates__"})
        if package_index_ids:
            package_ids = package_ids.union(package_index_ids)
        tool_ids = registry_ids(self._references(workplace_manifest).load_workplace_registry(workplace_manifest, "tools", "tools.yaml"), "tools")
        mcp_ids = registry_ids(self._references(workplace_manifest).load_workplace_registry(workplace_manifest, "mcp", "mcp.yaml"), "mcp_servers")
        templates_registry = self._references(workplace_manifest).load_workplace_registry(workplace_manifest, "templates", "templates.yaml")
        template_ids = registry_ids(templates_registry, "template_roots").union(registry_ids(templates_registry, "templates"))
        required_missing: list[dict[str, Any]] = []
        recommended_missing: list[dict[str, Any]] = []

        for group, available, collection in [
            ("knowledge_package", package_ids, resolved.get("required_knowledge_packages", [])),
            ("tool", tool_ids, resolved.get("required_tools", [])),
            ("mcp", mcp_ids, resolved.get("required_mcp", [])),
            ("template", template_ids, resolved.get("required_templates", [])),
        ]:
            for item in collection:
                if item not in available:
                    required_missing.append({"kind": group, "id": item, "status": "missing", "severity": "fail", "requirement": "required"})

        for group, available, collection in [
            ("knowledge_package", package_ids, resolved.get("recommended_knowledge_packages", [])),
            ("tool", tool_ids, resolved.get("recommended_tools", [])),
            ("mcp", mcp_ids, resolved.get("recommended_mcp", [])),
            ("template", template_ids, resolved.get("recommended_templates", [])),
        ]:
            for item in collection:
                if item not in available:
                    recommended_missing.append({"kind": group, "id": item, "status": "missing", "severity": "warn", "requirement": "recommended"})
        return required_missing, recommended_missing

    def binding_matches(self, binding: dict[str, Any], selected_platforms: list[str], platform_stack: list[dict[str, Any]], process_id: str | None = None) -> bool:
        selected = {self.contracts.contract_id(item) for item in selected_platforms}
        stack_ids = {str(item.get("id") or self.contracts.contract_id(str(item.get("platform") or ""))) for item in platform_stack if isinstance(item, dict)}
        binding_platforms = {self.contracts.contract_id(item) for item in list_value(binding.get("platforms"))}
        stack_includes = {self.contracts.contract_id(item) for item in list_value(binding.get("platform_stack_includes"))}
        process_filter = set(list_value(binding.get("applies_to_processes")))
        if process_filter and process_id and process_id not in process_filter:
            return False
        return bool(selected.intersection(binding_platforms) or stack_ids.intersection(stack_includes))

    def optional_warnings(self, workplace_manifest: Path | None, resolved: dict[str, Any], package_index_ids: set[str] | None = None) -> list[dict[str, Any]]:
        _required_missing, recommended_missing = self.resource_findings(workplace_manifest, resolved, package_index_ids)
        return recommended_missing

    def forbidden_base_reference(self, text: str) -> bool:
        policy = self.documents.policy("platform-id-policy.yaml", distribution_root=self.distribution_root)
        discouraged = [
            str(item.get("id") if isinstance(item, dict) else item)
            for item in policy.get("discouraged_platform_ids", [])
            if (item.get("id") if isinstance(item, dict) else item)
        ]
        if not discouraged:
            return False
        allowed_markers = [
            "incorrect",
            "discouraged",
            "do not create",
            "not as platform contracts",
            "not platform contracts",
            "не создавайте",
            "а не как platform contracts",
            "не как platform contracts",
            "не являются platform contracts",
        ]
        lines = text.splitlines()
        for index, line in enumerate(lines):
            lower = line.lower()
            matched = [platform_id for platform_id in discouraged if platform_id.lower() in lower]
            if not matched:
                continue
            context = " ".join(lines[max(0, index - 2) : min(len(lines), index + 3)]).lower()
            allowed_discouraged_example = any(marker in context for marker in allowed_markers)
            if not allowed_discouraged_example:
                return True
        return False

    def available_records(self, workplace_manifest: Path | None, project_root: Path | None = None) -> list[dict[str, Any]]:
        if not workplace_manifest or not workplace_manifest.is_file():
            return []
        registry = self._references(workplace_manifest, project_root).load_workplace_registry(workplace_manifest, "platforms", "platforms.yaml")
        entries = registry.get("platforms") if isinstance(registry, dict) else []
        records: list[dict[str, Any]] = []
        if not isinstance(entries, list):
            return records
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("status", "available")) in {"missing", "disabled"}:
                continue
            raw_id = str(entry.get("package_id") or entry.get("id") or "")
            if not raw_id:
                continue
            platform_id, contract_id = self.contracts.normalize_id_pair(raw_id)
            records.append(
                {
                    "id": contract_id,
                    "platform": platform_id,
                    "registry_entry": str(entry.get("id") or platform_id),
                    "source": str(entry.get("path") or ""),
                    "status": "available",
                }
            )
        return sorted(records, key=lambda item: item["id"])
