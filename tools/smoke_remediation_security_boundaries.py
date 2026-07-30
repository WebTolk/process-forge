#!/usr/bin/env python3
"""Regression smoke for resource authoring path-security boundaries."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import processforge
from specialization_smoke_helpers import read_yaml, run_pf, write_workspace, write_yaml


INVALID_RESOURCE_IDS = [
    "../escaped",
    "..\\escaped",
    "C:" + "\\escaped",
    "//server/share",
    "docs/escaped",
    "docs\\escaped",
    "docs%2fescaped",
    "docs%5cescaped",
    "docs.%2e%2e.escaped",
    "docs%252fescaped",
    "docs:escaped",
    "docs escaped",
    "docs.",
    "docs ",
    "con",
    "con.example",
    "prn",
    "aux",
    "nul",
    "com1",
    "com9",
    "lpt1",
    "lpt9",
]


def tree_fingerprint(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def require_rejected_without_write(workplace: Path, command: str, resource_id: str, *, apply: bool) -> None:
    before = tree_fingerprint(workplace.parent)
    args = [command, "--workplace", str(workplace), "--id", resource_id, "--title", "Boundary Fixture"]
    if command == "knowledge-package-create":
        args.extend(["--package-root", "global", "--kind", "documentation"])
    if apply:
        args.append("--apply")
    result = run_pf(*args)
    if result.returncode == 0:
        raise AssertionError(f"{command} accepted unsafe id {resource_id!r} (apply={apply}):\n{result.stdout}")
    if "invalid" not in result.stdout.lower():
        raise AssertionError(f"{command} did not explain invalid id {resource_id!r}:\n{result.stdout}")
    after = tree_fingerprint(workplace.parent)
    if after != before:
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
        raise AssertionError(
            f"{command} mutated the tree for unsafe id {resource_id!r} "
            f"(apply={apply}); added={added}, removed={removed}, changed={changed}"
        )


def main() -> int:
    for invalid_control_id in ["docs.\x01escaped", "docs.\x7fescaped"]:
        try:
            processforge.validate_resource_id(invalid_control_id, "fixture")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"resource id control character was accepted: {invalid_control_id!r}")

    with tempfile.TemporaryDirectory(prefix="pf-remediation-boundary-") as raw:
        root = Path(raw)
        workplace = write_workspace(root)
        for command in ["knowledge-package-create", "specialization-create"]:
            for resource_id in INVALID_RESOURCE_IDS:
                require_rejected_without_write(workplace, command, resource_id, apply=False)
                require_rejected_without_write(workplace, command, resource_id, apply=True)

        hub = root / "hub"
        before_hub = tree_fingerprint(root)
        for args in [
            [
                "knowledge-package-build-from-candidates",
                "--hub",
                str(hub),
                "--package",
                "../escaped",
                "--version",
                "1.0.0",
                "--apply",
            ],
            [
                "knowledge-package-release",
                "--hub",
                str(hub),
                "--package",
                "../escaped",
                "--version",
                "1.0.0",
                "--output",
                str(root / "escaped.zip"),
            ],
        ]:
            result = run_pf(*args)
            if result.returncode == 0 or "invalid" not in result.stdout.lower():
                raise AssertionError("hub command accepted unsafe package id:" + "\n" + result.stdout)
            if tree_fingerprint(root) != before_hub:
                raise AssertionError(f"hub command mutated the tree before rejecting unsafe package id: {args[0]}")

        outside_specialization = root / "outside-specialization.yaml"
        write_yaml(
            outside_specialization,
            {
                "schema_version": 1,
                "kind": "processforge.specialization",
                "id": "specialization.registry-escape",
            },
        )
        registry_path = workplace / "registries" / "specializations.yaml"
        registry = read_yaml(registry_path)
        registry["specializations"] = [
            {
                "id": "specialization.registry-escape",
                "path": "../outside-specialization.yaml",
                "status": "available",
            }
        ]
        write_yaml(registry_path, registry)
        registry_before = tree_fingerprint(root)
        registry_result = run_pf(
            "specialization-doctor",
            "--workplace",
            str(workplace),
            "--id",
            "specialization.registry-escape",
        )
        if registry_result.returncode == 0 or "contained" not in registry_result.stdout.lower():
            raise AssertionError("specialization registry path escape was not rejected:" + "\n" + registry_result.stdout)
        if tree_fingerprint(root) != registry_before:
            raise AssertionError("specialization-doctor mutated the tree while rejecting a registry path escape")
        write_yaml(registry_path, {"schema_version": 1, "specializations": []})

        package_id = "docs.example-v1"
        package_result = run_pf(
            "knowledge-package-create",
            "--workplace",
            str(workplace),
            "--id",
            package_id,
            "--title",
            "Valid Dotted Package",
            "--package-root",
            "global",
            "--kind",
            "documentation",
            "--apply",
        )
        if package_result.returncode != 0:
            raise AssertionError(package_result.stdout)
        if not (workplace / "packages" / package_id / "package.yaml").is_file():
            raise AssertionError("valid dotted/dashed knowledge package id was not preserved")

        external_packages = root / "external-packages"
        external_packages.mkdir()
        package_roots_path = workplace / "registries" / "package-roots.yaml"
        package_roots = read_yaml(package_roots_path)
        package_roots["package_roots"].append(
            {
                "id": "external",
                "path": "../external-packages",
                "status": "available",
                "writable": True,
            }
        )
        write_yaml(package_roots_path, package_roots)
        external_id = "docs.example-external-v1"
        external_result = run_pf(
            "knowledge-package-create",
            "--workplace",
            str(workplace),
            "--id",
            external_id,
            "--title",
            "Valid External Root Package",
            "--package-root",
            "external",
            "--kind",
            "documentation",
            "--apply",
        )
        if external_result.returncode != 0:
            raise AssertionError(external_result.stdout)
        if not (external_packages / external_id / "package.yaml").is_file():
            raise AssertionError("valid package was not contained in its declared external package root")

        specialization_id = "specialization.release-auditor-v2"
        specialization_result = run_pf(
            "specialization-create",
            "--workplace",
            str(workplace),
            "--id",
            specialization_id,
            "--title",
            "Valid Dotted Specialization",
            "--apply",
        )
        if specialization_result.returncode != 0:
            raise AssertionError(specialization_result.stdout)
        if not (workplace / "specializations" / f"{specialization_id}.yaml").is_file():
            raise AssertionError("valid dotted/dashed specialization id was not preserved")

    print("PASS: remediation resource authoring security boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
