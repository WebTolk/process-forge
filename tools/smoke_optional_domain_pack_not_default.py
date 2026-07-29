#!/usr/bin/env python3
"""Smoke that optional domain examples are not in default resolver roots."""

from smoke_domain_neutral_core_helpers import DOMAIN_CORE_PROCESS_IDS, ROOT, load_processforge


def main() -> None:
    pf = load_processforge()
    root_packages = {path.stem for path in (ROOT / "packages").glob("*.yaml")}
    if root_packages.intersection({"process-forge-software-development", "process-forge-content", "process-forge-testing"}):
        raise AssertionError(root_packages)
    core_processes = {path.stem for path in (ROOT / "processes" / "core").glob("*.yaml")}
    if core_processes.intersection(DOMAIN_CORE_PROCESS_IDS):
        raise AssertionError(core_processes.intersection(DOMAIN_CORE_PROCESS_IDS))
    for path in (ROOT / "examples" / "domain-packs").glob("*/package.yaml"):
        package = pf.load_yaml_document(path)
        if package.get("status") != "optional_example" or package.get("core") is not False or package.get("installed_by_default") is not False:
            raise AssertionError(f"invalid optional pack metadata: {path}")
    print("PASS: smoke_optional_domain_pack_not_default")


if __name__ == "__main__":
    main()
