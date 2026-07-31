#!/usr/bin/env python3
"""Smoke neutral parameter cascade resolution."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-parameter-cascade-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        workplace_manifest = workplace / "workplace.yaml"
        workplace_data = read_yaml(workplace_manifest)
        workplace_data.setdefault("registries", {})["parameters"] = "registries/parameters.yaml"
        write_yaml(workplace_manifest, workplace_data)
        write_yaml(
            workplace / "registries" / "parameters.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.parameters",
                "scope": "workplace",
                "parameters": {
                    "joomla": {
                        "active_test_stand": "stand1",
                        "test_stands": [
                            {
                                "id": "stand1",
                                "url": "http://stand1.local",
                                "admin_url": "http://stand1.local/administrator",
                                "user": "login1",
                                "password": "password1",
                            },
                            {
                                "id": "stand2",
                                "url": "http://stand2.local",
                                "auth_ref": "workspace.stand2",
                            },
                        ],
                    }
                },
            },
        )
        child_contract_path = workplace / "platform-contracts" / "fixture.platform.child" / "platform-contract.yaml"
        child_contract = read_yaml(child_contract_path)
        child_contract["parameters"] = {"joomla": {"platform_flag": "child-platform"}}
        write_yaml(child_contract_path, child_contract)
        write_specialization(workplace, "fixture.specialization.parameters")
        specialization_path = workplace / "specializations" / "fixture.specialization.parameters.yaml"
        specialization = read_yaml(specialization_path)
        specialization["parameters"] = {"joomla": {"specialization_flag": "enabled"}}
        specialization["platform_bindings"][0]["parameters"] = {"joomla": {"binding_flag": "child"}}
        write_yaml(specialization_path, specialization)
        project = write_project(root, workplace, specializations=["fixture.specialization.parameters"])
        write_yaml(
            project / ".pf" / "parameters.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.parameters",
                "scope": "project",
                "parameters": {
                    "joomla": {
                        "test_stands": [
                            {
                                "id": "stand1",
                                "user": "login2",
                                "password": "password2",
                            }
                        ]
                    }
                },
            },
        )
        (project / ".pf" / "AGENTS.md").write_text(
            "\n".join(["# AGENTS", "", "parameters:", "  joomla:", "    active_test_stand: should-not-apply", ""]),
            encoding="utf-8",
        )
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        snapshot = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        params = snapshot["resolved_parameters"]["joomla"]
        if params["active_test_stand"] != "stand1":
            raise AssertionError("workplace scalar was not inherited")
        stand1 = next(item for item in params["test_stands"] if item["id"] == "stand1")
        if stand1["url"] != "http://stand1.local":
            raise AssertionError("project list item override replaced inherited fields")
        if stand1["user"] != "login2" or stand1["password"] != "password2":
            raise AssertionError("project list item override did not win")
        if params["active_test_stand"] == "should-not-apply":
            raise AssertionError("AGENTS.md was parsed as parameters")
        if params["platform_flag"] != "child-platform":
            raise AssertionError("platform parameters were not merged")
        if params["specialization_flag"] != "enabled" or params["binding_flag"] != "child":
            raise AssertionError("specialization parameters were not merged")
        if "parameter_resolution" not in snapshot:
            raise AssertionError("parameter resolution metadata missing")
    print("PASS: smoke_parameter_cascade_resolution")


if __name__ == "__main__":
    main()
