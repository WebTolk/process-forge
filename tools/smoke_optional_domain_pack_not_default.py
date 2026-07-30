#!/usr/bin/env python3
"""Compatibility smoke that bundled domain packs remain inactive by default."""

from smoke_domain_neutral_core_helpers import DOMAIN_CORE_PROCESS_IDS, ROOT, load_processforge


def main() -> None:
    pf = load_processforge()
    root_packages = {path.stem for path in (ROOT / "packages").glob("*.yaml")}
    if root_packages.intersection({"process-forge-software-development", "process-forge-content", "process-forge-testing"}):
        raise AssertionError(root_packages)
    core_processes = {path.stem for path in (ROOT / "processes" / "core").glob("*.yaml")}
    if core_processes.intersection(DOMAIN_CORE_PROCESS_IDS):
        raise AssertionError(core_processes.intersection(DOMAIN_CORE_PROCESS_IDS))
    manifests = sorted((ROOT / "packs" / "official").glob("*/package.yaml"))
    if len(manifests) != 3:
        raise AssertionError(manifests)
    for path in manifests:
        package = pf.load_yaml_document(path)
        activation = package.get("activation", {})
        if (
            package.get("origin") != "official"
            or package.get("core_runtime_dependency") is not False
            or activation.get("available_by_default") is not True
            or activation.get("active_by_default") is not False
        ):
            raise AssertionError(f"invalid bundled pack activation metadata: {path}")
    print("PASS: smoke_optional_domain_pack_not_default")


if __name__ == "__main__":
    main()
