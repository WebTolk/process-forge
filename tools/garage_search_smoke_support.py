"""Shared temporary Workplace fixtures for Garage search smokes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


def register_fixture_resource(
    workplace: Path,
    package_id: str,
    resource_id: str,
    files: dict[str, str],
    *,
    title: str,
) -> str:
    """Register a package/resource through the public Workplace contract."""

    run_cli(
        "knowledge-package-create",
        "--workplace",
        str(workplace),
        "--id",
        package_id,
        "--title",
        title,
        "--package-root",
        "global",
        "--kind",
        "documentation",
        "--apply",
    )
    package_root = workplace / "packages" / package_id
    resource_root = package_root / "resources" / resource_id
    resource_root.mkdir(parents=True, exist_ok=True)
    for relative_path, content in files.items():
        target = resource_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    resource_file = workplace.parent / f"{package_id}-{resource_id}-resource.yaml"
    resource_file.write_text(
        yaml.safe_dump(
            {
                "id": resource_id,
                "kind": "documentation",
                "title": title,
                "load_policy": "when_relevant",
                "path_ref": {
                    "registry": "package_roots",
                    "id": "global",
                    "relative_path": f"{package_id}/resources/{resource_id}",
                },
                # Resource management currently accepts this compatibility
                # field and derives the explicit search policy from it.
                "index_policy": "fulltext",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    run_cli(
        "knowledge-add-resource",
        "--workplace",
        str(workplace),
        "--package",
        package_id,
        "--package-root",
        "global",
        "--resource-file",
        str(resource_file),
        "--apply",
    )
    return f"{package_id}:{resource_id}"


def select_fixture_resource(project: Path, workplace: Path, package_id: str, resource_id: str) -> None:
    """Select a registered package/resource using normal project refresh."""

    manifest_path = project / ".pf" / "process-forge.yaml"
    manifest: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    stack = manifest.setdefault("knowledge_stack", [])
    if not any(isinstance(item, dict) and item.get("id") == package_id for item in stack):
        stack.append({"id": package_id, "version": "1.0.0", "source": "workplace"})
    requirements = manifest.setdefault("context_requirements", {})
    packages = requirements.setdefault("knowledge_packages", [])
    if not any(isinstance(item, dict) and item.get("id") == package_id for item in packages):
        packages.append({"id": package_id, "constraint": "*", "required": True})
    resources = requirements.setdefault("knowledge_resources", [])
    if not any(isinstance(item, dict) and item.get("id") == resource_id for item in resources):
        resources.append({"id": resource_id, "constraint": "*", "required": True})
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run_cli(
        "project-context-refresh",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--apply",
    )


def empty_fixture_authorization(project: Path, workplace: Path) -> None:
    """Refresh a project whose manifest selects no searchable resources."""

    manifest_path = project / ".pf" / "process-forge.yaml"
    manifest: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest["knowledge_stack"] = [item for item in manifest.get("knowledge_stack", []) if isinstance(item, dict) and item.get("id") == "processforge.core"]
    requirements = manifest.setdefault("context_requirements", {})
    requirements["knowledge_packages"] = [item for item in requirements.get("knowledge_packages", []) if isinstance(item, dict) and item.get("id") == "processforge.core"]
    requirements["knowledge_resources"] = []
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run_cli(
        "project-context-refresh",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--apply",
    )
