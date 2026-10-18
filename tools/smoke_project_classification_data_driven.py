#!/usr/bin/env python3
"""Smoke that project classification changes only with loaded classifier data."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from smoke_domain_neutral_core_helpers import load_processforge


def check_flow_state_markers(pf, root: Path) -> None:
    project = root / "receipt-project"
    receipt = project / ".pf" / "artifacts" / "delivery" / "package.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"artifact": "package-receipt"}\n', encoding="utf-8")
    classifier = pf.ROOT / "packs/official/software-development/project-classifiers/software-web.yaml"
    classified = pf.classify_project(project, explicit_classifier_paths=[classifier])
    assert classified["project_types"] == [], classified
    assert classified["inactive_classifier_hints"] == [], classified
    assert pf.inactive_official_classifier_hints(None, project) == []
    assert receipt in pf.list_project_files(project), "generic inventory must retain PF evidence"
    assert not any(path == ".pf" or path.startswith(".pf/") for path in pf.project_available_paths(project))

    (project / "main.py").write_text("pass\n", encoding="utf-8")
    python_only = pf.classify_project(project, explicit_classifier_paths=[classifier])
    assert python_only["project_types"] == ["software.python"], python_only
    for relative in ("package.json", "application/frontend/package.json"):
        actual = project / relative
        actual.parent.mkdir(parents=True, exist_ok=True)
        actual.write_text("{}\n", encoding="utf-8")
        with_application = pf.classify_project(project, explicit_classifier_paths=[classifier])
        assert with_application["project_types"] == ["software.javascript-node", "software.python"], with_application
        actual.unlink()


def check_marker_parity(pf, root: Path) -> None:
    """Local classifier data remains readable despite pruning flow inventory."""
    rules = (("php", "composer.json"), ("node", "frontend/package.json"),
             ("joomla", "administrator/manifests/files/joomla.xml"))
    for kind, relative in (*rules, ("unclassified", "README.md")):
        project = root / f"parity-{kind}"
        marker = project / relative
        marker.parent.mkdir(parents=True)
        marker.write_text("fixture\n", encoding="utf-8")
        flow = project / ".pf"
        pf.write_yaml_file(flow / "project-classifiers" / "fixture.yaml", {
            "schema_version": 1, "kind": "processforge.project_classifier",
            "id": "fixture.parity", "status": "active",
            "rules": [{"id": name, "when": {"all": [{"exists": path}]},
                       "classify_as": {"project_types": [f"fixture.{name}"]}}
                      for name, path in rules],
        })
        pf.write_yaml_file(flow / "registries" / "project-classifiers.yaml", {
            "schema_version": 1, "project_classifiers": [
                {"id": "fixture.parity", "path": "project-classifiers/fixture.yaml", "status": "active"}],
        })
        receipt = flow / "artifacts" / "frontend" / "package.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("{}\n", encoding="utf-8")
        actual = pf.classify_project(project)
        with patch.object(pf, "list_classifier_files", pf.list_project_files):
            previous = pf.classify_project(project)
        assert actual == previous, (actual, previous)
        assert actual["loaded_classifiers"] == ["fixture.parity"], actual
        assert actual["project_types"] == ([] if kind == "unclassified" else [f"fixture.{kind}"]), actual


def main() -> None:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-classifier-data-") as tmp:
        root = Path(tmp)
        project = root / "project"
        project.mkdir()
        (project / "fixture.marker").write_text("fixture\n", encoding="utf-8")
        without = pf.detect_project(project)
        if without["status"] != "unclassified" or without["project_kind"] != ["unknown"]:
            raise AssertionError(without)
        classifier = root / "fixture.classifier.yaml"
        classifier.write_text((pf.ROOT / "templates" / "project-classifier.yaml").read_text(encoding="utf-8"), encoding="utf-8")
        with_classifier = pf.detect_project(project, explicit_classifier_paths=[classifier])
        if with_classifier["status"] != "classified":
            raise AssertionError(with_classifier)
        if with_classifier["project_kind"] != ["fixture.project-type.a"]:
            raise AssertionError(with_classifier)

        flow = project / ".pf"
        (flow / "registries").mkdir(parents=True)
        (flow / "project-classifiers").mkdir()
        (flow / "platform-contracts").mkdir()
        (flow / "process-forge.yaml").write_text(
            """schema_version: 1
process_forge:
  version: 1.0.0
project:
  id: fixture-project
  type: unknown
paths:
  contexts: contexts
  runtime: runtime
policies: {}
required_capabilities: []
optional_capabilities: []
""",
            encoding="utf-8",
        )
        classifier_target = flow / "project-classifiers" / classifier.name
        classifier_target.write_text(classifier.read_text(encoding="utf-8"), encoding="utf-8")
        (flow / "platform-contracts" / "fixture-a.yaml").write_text(
            """schema_version: 1
id: platform.example.fixture-a
type: platform_contract
version: "1.0.0"
applies_to:
  platforms:
    - example.fixture-a
requires:
  capabilities: []
  tools: []
  mcp: []
  templates: []
includes:
  knowledge_packages: []
  tools: []
  mcp: []
  templates: []
""",
            encoding="utf-8",
        )
        (flow / "registries" / "project-classifiers.yaml").write_text(
            f"""schema_version: 1
project_classifiers:
  - id: fixture.classifier.a
    path: project-classifiers/{classifier.name}
    status: active
""",
            encoding="utf-8",
        )
        (project / "fixture.marker").unlink()
        pf.write_project_context_snapshot_outputs(project)
        (project / "fixture.marker").write_text("fixture\n", encoding="utf-8")
        freshness = pf.project_context_check_result(project)
        if freshness["status"] != "stale":
            raise AssertionError(freshness)
        if not any(item.get("reason") == "project classification changed" for item in freshness["stale_resources"]):
            raise AssertionError(freshness)
        check_flow_state_markers(pf, root)
        check_marker_parity(pf, root)
    print("PASS: smoke_project_classification_data_driven")


if __name__ == "__main__":
    main()
