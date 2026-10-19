"""Audit the built-in process catalog through concrete Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.paths import rel
from processforge_core.common.values import string_list
from processforge_core.common.yaml_io import _parse_simple_yaml, yaml_error
from processforge_core.documents.reader import YamlDocumentReader

from .artifacts import ProcessArtifactDeclarationPolicy
from .catalog_read import ProcessCatalogReadService
from .contracts import ProcessContractValidationService
from .service import process_catalog_contexts, process_catalog_metadata, process_is_public_stable
from .validation import ProcessAuthoringValidationService


class BuiltinProcessCatalogAuditService:
    """Own the existing ordered catalog report and flat package index."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.documents = YamlDocumentReader(_parse_simple_yaml)
        self.contracts = ProcessContractValidationService(distribution_root)
        self.authoring = ProcessAuthoringValidationService()
        self.artifacts = ProcessArtifactDeclarationPolicy()

    def report(self, root: Path, *, public: bool = False) -> dict[str, Any]:
        process_items = ProcessCatalogReadService(root, distribution_root=self.distribution_root).entries(strict=True)
        process_ids = {entry.process_id for entry in process_items}
        packages = self.package_index(root)
        rows: list[dict[str, Any]] = []
        summary: dict[str, int] = {
            "processes": 0,
            "public_stable": 0,
            "public_experimental": 0,
            "internal": 0,
            "fail": 0,
            "warn": 0,
            "pass": 0,
        }
        checks: list[Check] = []
        for entry in process_items:
            process_id = entry.process_id
            path = entry.path
            process = entry.process
            meta = process_catalog_metadata(process)
            if public and meta["classification"] == "INTERNAL_MAINTENANCE":
                strict_checks = [check("PASS", f"{process_id} internal maintenance process skipped by public catalog doctor")]
            else:
                strict_checks = self.contracts.validate(
                    root,
                    process,
                    path,
                    strict=process_is_public_stable(process),
                    companion_root=entry.root if entry.origin == "official" else root,
                )
            failures = [item.message for item in strict_checks if item.level == "FAIL"]
            warnings = [item.message for item in strict_checks if item.level == "WARN"]
            checks.extend(strict_checks)
            if meta["classification"] == "PUBLIC_STABLE":
                summary["public_stable"] += 1
            elif meta["classification"] == "PUBLIC_EXPERIMENTAL":
                summary["public_experimental"] += 1
            elif meta["classification"] == "INTERNAL_MAINTENANCE":
                summary["internal"] += 1
            summary["processes"] += 1
            summary["fail"] += len(failures)
            summary["warn"] += len(warnings)
            if not failures:
                summary["pass"] += 1
            process_pack = process.get("process_pack") if isinstance(process.get("process_pack"), dict) else {}
            package_id = str(process_pack.get("package") or (string_list(process.get("required_packages"))[0] if string_list(process.get("required_packages")) else ""))
            companions = self.authoring.paths(entry.root if entry.origin == "official" else root, process_id)
            rows.append(
                {
                    "id": process_id,
                    "path": rel(path, root),
                    "origin": entry.origin,
                    "root": rel(entry.root, root),
                    "catalog_role": entry.catalog_role,
                    "status": process.get("status"),
                    "classification": meta["classification"],
                    "public_surface": meta["public_surface"],
                    "package": package_id,
                    "execution_mode": process.get("execution_mode"),
                    "coordination_mode": (process.get("coordination_requirements") or {}).get("mode") if isinstance(process.get("coordination_requirements"), dict) else None,
                    "error_handling": (process.get("error_handling") or {}).get("mode") if isinstance(process.get("error_handling"), dict) else None,
                    "has_prompt": companions["prompt"].is_file(),
                    "has_process_doc": companions["doc"].is_file(),
                    "has_authoring_example": companions["example"].is_file(),
                    "artifact_definitions_complete": not (self.artifacts.produced_ids(process) - self.artifacts.declared_ids(process)),
                    "stage_artifacts_declared": not (self.artifacts.produced_ids(process) - self.artifacts.declared_ids(process)),
                    "gates_valid": not any("gates valid:" in item.message and item.level == "FAIL" for item in strict_checks),
                    "handoff_semantics": "process_transition" if process.get("process_transitions") else ("run_summary" if process.get("run_completion") else ("stage_note" if process.get("stage_completion") else "none")),
                    "doctor_contexts": process_catalog_contexts(process),
                    "result": "fail" if failures else ("warn" if warnings else "pass"),
                    "failures": failures,
                    "warnings": warnings + entry.warnings,
                }
            )

        for package_id, item in packages.items():
            package_data = item["data"]
            for process_id in item["processes"]:
                checks.append(check("PASS" if process_id in process_ids else "FAIL", f"package {package_id} process id exists: {process_id}"))
            stable_exposed = set(string_list(package_data.get("stable_processes")))
            for process_id in stable_exposed:
                process = next((entry.process for entry in process_items if entry.process_id == process_id), {})
                checks.append(check("PASS" if process_is_public_stable(process) else "FAIL", f"package {package_id} stable process is public stable: {process_id}"))

        package_failures = [item.message for item in checks if item.level == "FAIL" and item.message.startswith("package ")]
        summary["fail"] += len(package_failures)
        return {"schema_version": 1, "summary": summary, "processes": rows, "checks": [{"level": item.level, "message": item.message} for item in checks]}

    def package_index(self, root: Path) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for path in sorted((root / "packages").glob("*.yaml")):
            data = self.documents.load(path)
            if yaml_error(data) or not isinstance(data, dict):
                continue
            package_id = str(data.get("id") or path.stem)
            index[package_id] = {"path": path, "data": data, "processes": string_list(data.get("processes"))}
        return index
