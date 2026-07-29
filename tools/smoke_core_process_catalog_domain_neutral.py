#!/usr/bin/env python3
"""Smoke that domain workflow IDs are absent from the canonical core catalog."""

from smoke_domain_neutral_core_helpers import DOMAIN_CORE_PROCESS_IDS, ROOT, load_processforge


def main() -> None:
    pf = load_processforge()
    entries = pf.process_catalog_entries(ROOT, strict=True)
    violations = [
        entry.process_id
        for entry in entries
        if entry.origin == "core" and entry.process_id in DOMAIN_CORE_PROCESS_IDS
    ]
    if violations:
        raise AssertionError(violations)
    core_package = pf.load_yaml_document(ROOT / "packages" / "process-forge-core.yaml")
    if DOMAIN_CORE_PROCESS_IDS.intersection(set(core_package.get("processes", []))):
        raise AssertionError(core_package.get("processes"))
    print("PASS: smoke_core_process_catalog_domain_neutral")


if __name__ == "__main__":
    main()
