"""Validate platform contracts through concrete Core resource owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from ..common.policies import policy_entries, policy_id_matches
from ..common.text import check_with_hint
from ..common.values import list_value
from ..resources.project_packages import ProjectPackageCatalogReader
from ..work.context_documents import ContextContractInputs
from .platform_policy import PlatformContractPolicy
from .platform_resolution import PlatformContractResolver
from .platform_selection import ProjectPlatformSelectionService
from .platforms import PlatformContractReader
from .templates import TemplateCatalogService


class PlatformContractValidationService:
    """Preserve the existing ordered platform semantic checks."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self._platform_contract_reader = PlatformContractReader(distribution_root)
        self._platform_contract_policy = PlatformContractPolicy(self._platform_contract_reader)
        self._platform_contract_resolver = PlatformContractResolver(distribution_root)
        self._project_platform_selection_service = ProjectPlatformSelectionService(distribution_root)
        self._project_package_catalog_reader = ProjectPackageCatalogReader(distribution_root)
        self._context_contract_inputs = ContextContractInputs()
        self._templates = TemplateCatalogService(distribution_root)

    def validate(
        self,
        workplace_root: Path,
        data: dict[str, Any],
        platform: str,
        *,
        platform_resolution: dict[str, Any] | None = None,
    ) -> list[Check]:
        checks: list[Check] = []
        checks.append(check("PASS" if data.get("id") else "FAIL", "platform contract id present"))
        contract_id = self._platform_contract_reader.contract_id(str(data.get("id") or platform))
        for entry in policy_entries(self._context_contract_inputs.documents.policy("platform-id-policy.yaml", distribution_root=self.distribution_root), "discouraged_platform_ids"):
            if policy_id_matches(contract_id, entry):
                checks.append(
                    check_with_hint(
                        str(entry.get("user_created_behavior", "WARN")).upper(),
                        str(entry.get("message", f"platform id discouraged: {contract_id}")),
                        str(entry.get("why", "The platform id matched a data-driven platform id policy.")),
                        str(entry.get("fix", "update the platform id or policy manifest")),
                    )
                )
        hints = data.get("project_type_hints")
        if not isinstance(hints, list):
            applies_to = data.get("applies_to") if isinstance(data.get("applies_to"), dict) else {}
            hints = applies_to.get("project_type_hints") if isinstance(applies_to.get("project_type_hints"), list) else []
        checks.append(check("PASS" if isinstance(hints, list) and hints else "WARN", "project_type_hints configured"))
        requires = data.get("requires") if isinstance(data.get("requires"), dict) else {}
        checks.append(check("PASS" if requires.get("capabilities") else "WARN", "required capabilities listed"))
        extends_refs = self._platform_contract_policy.extends(data)
        required_platform_refs = self._platform_contract_policy.required_platforms(data)
        checks.append(check("PASS", "extends entries are valid") if all(ref.get("id") for ref in extends_refs) else check("FAIL", "extends entries are valid"))
        checks.append(check("PASS", "requires.platforms entries are valid") if all(ref.get("id") for ref in required_platform_refs) else check("FAIL", "requires.platforms entries are valid"))
        for ref in extends_refs:
            if ref.get("required") is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"extends parent is required: {ref['id']}",
                        "Platform inheritance cannot be optional in the pre-release contract model.",
                        "set required: true or move the platform reference to requires.platforms if it is only a dependency",
                    )
                )
        required_platform_by_id = {str(ref["id"]): bool(ref.get("required", True)) for ref in required_platform_refs}
        for ref in extends_refs:
            if required_platform_by_id.get(str(ref["id"])) is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"child platform cannot weaken required parent dependency: {ref['id']}",
                        "An inherited parent is required by definition; requires.platforms cannot mark the same parent optional.",
                        "set requires.platforms[].required: true for the parent platform",
                    )
                )
        platform_resolution = platform_resolution or self._platform_contract_resolver.resolve(workplace_root / "workplace.yaml", [data.get("id") or platform])
        for missing in platform_resolution["missing_required_contracts"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required platform available: {missing}",
                    "The platform contract extends or requires a platform that is not registered in the workplace.",
                    f"python bin/pf.py platform-create --workplace <workplace-root> --id {missing} --title \"{missing}\" --apply",
                )
            )
        for cycle in platform_resolution["circular_platforms"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"circular platform inheritance detected: {cycle}",
                    "Platform inheritance must resolve to an acyclic parent-first stack.",
                    "remove one extends edge from the cycle and rerun platform-contract-doctor",
                )
            )
        checks.append(check("PASS" if platform_resolution["platform_stack"] else "FAIL", "resolved platform stack valid"))
        checks.append(check("PASS", "resolved platform stack computed without mutating workplace state"))
        inherited_required, inherited_recommended = self._project_platform_selection_service.resource_findings(workplace_root / "workplace.yaml", platform_resolution)
        for item in inherited_required:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack marks this resource as required.",
                    "register the missing resource in the workplace registry or package roots before using this platform",
                )
            )
        for item in inherited_recommended:
            checks.append(
                check_with_hint(
                    "WARN",
                    f"optional {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack recommends this resource, but onboarding can continue.",
                    "register the resource if this platform should provide the optional capability",
                )
            )
        for package_id in list_value(requires.get("knowledge_packages")):
            manifest = self._project_package_catalog_reader.index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"required knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "FAIL",
                    f"required knowledge package available: {package_id}",
                    "This platform contract marks the package as required.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                    "mark it as required: false or move it to includes.knowledge_packages if optional",
                )
            )
        for package_id in self._platform_contract_policy.includes(data, "knowledge_packages"):
            manifest = self._project_package_catalog_reader.index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"optional knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "WARN",
                    f"optional knowledge package available: {package_id}",
                    "This platform contract recommends the package, but onboarding can continue.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                )
            )
        for template_id in list_value(requires.get("templates")):
            checks.append(
                check("PASS", f"required template available: {template_id}")
                if self._templates.manifest(workplace_root, template_id)
                else check_with_hint(
                    "FAIL",
                    f"required template available: {template_id}",
                    "This platform contract marks the template as required.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                    "move it to includes.templates if optional",
                )
            )
        for template_id in self._platform_contract_policy.includes(data, "templates"):
            checks.append(
                check("PASS", f"optional template available: {template_id}")
                if self._templates.manifest(workplace_root, template_id)
                else check_with_hint(
                    "WARN",
                    f"optional template available: {template_id}",
                    "This platform contract recommends the template, but onboarding can continue without it.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                )
            )
        return checks
