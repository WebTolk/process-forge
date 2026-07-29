#!/usr/bin/env python3
"""Smoke that an empty workplace contains no active domain resources."""

import tempfile
from pathlib import Path

from smoke_domain_neutral_core_helpers import assert_no_domain_ids, load_processforge, run_pf, yaml_ids


def main() -> None:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-empty-neutral-") as tmp:
        workplace = Path(tmp) / "workplace"
        run_pf("workplace-init", "--workplace", str(workplace), "--apply")
        registry_keys = {
            "platforms.yaml": "platforms",
            "tools.yaml": "tools",
            "mcp.yaml": "mcp_servers",
            "templates.yaml": "templates",
            "specializations.yaml": "specializations",
            "project-classifiers.yaml": "project_classifiers",
        }
        for filename, key in registry_keys.items():
            path = workplace / "registries" / filename
            if not path.is_file():
                raise AssertionError(f"missing structural registry: {filename}")
            assert_no_domain_ids(yaml_ids(pf.load_yaml_document(path).get(key)), filename)
        classifier_registry = pf.load_yaml_document(workplace / "registries" / "project-classifiers.yaml")
        if classifier_registry.get("project_classifiers") != []:
            raise AssertionError(classifier_registry)
    print("PASS: smoke_empty_workplace_has_no_domain_resources")


if __name__ == "__main__":
    main()
