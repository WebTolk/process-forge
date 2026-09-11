#!/usr/bin/env python3
"""Smoke stable classifier provenance across disposable distribution roots."""

from __future__ import annotations

import tempfile
from pathlib import Path

from smoke_domain_neutral_core_helpers import load_processforge


CLASSIFIER_RELATIVE_PATH = Path("packs/official/fixture-pack/project-classifiers/fixture.yaml")
CLASSIFIER_TEMPLATE = """schema_version: 1
kind: processforge.project_classifier
id: fixture.distribution.classifier
name: Fixture Distribution Classifier
status: active
rules:
  - id: fixture.python-rule
    when:
      any:
        - exists: app.py
    classify_as:
      project_types:
        - {project_type}
      tags:
        - fixture
    confidence: high
"""


def make_distribution(root: Path, project_type: str) -> Path:
    (root / "bin").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "schemas").mkdir()
    (root / "processes" / "core").mkdir(parents=True)
    (root / "bin" / "pf.py").write_text("# fixture launcher\n", encoding="utf-8")
    (root / "tools" / "processforge.py").write_text("# fixture distribution marker\n", encoding="utf-8")
    (root / "schemas" / "process-definition.schema.json").write_text("{}\n", encoding="utf-8")
    classifier = root / CLASSIFIER_RELATIVE_PATH
    classifier.parent.mkdir(parents=True)
    classifier.write_text(CLASSIFIER_TEMPLATE.format(project_type=project_type), encoding="utf-8")
    return classifier


def classification_semantics(value: dict) -> dict:
    return {
        key: value.get(key)
        for key in [
            "status",
            "project_types",
            "platforms",
            "tags",
            "confidence",
            "loaded_classifiers",
            "matched_rules",
            "inactive_classifier_hints",
        ]
    }


def main() -> None:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-classifier-parity-") as tmp:
        root = Path(tmp)
        project = root / "project"
        project.mkdir()
        (project / "app.py").write_text("print('fixture')\n", encoding="utf-8")

        distribution_a = root / "distribution-a"
        distribution_b = root / "distribution-b"
        classifier_a = make_distribution(distribution_a, "fixture.python")
        classifier_b = make_distribution(distribution_b, "fixture.python")

        result_a = pf.classify_project(project, explicit_classifier_paths=[classifier_a])
        result_b = pf.classify_project(project, explicit_classifier_paths=[classifier_b])
        expected_source = CLASSIFIER_RELATIVE_PATH.as_posix()
        assert result_a["matched_rules"][0]["source"] == expected_source, result_a
        assert result_b["matched_rules"][0]["source"] == expected_source, result_b
        assert classification_semantics(result_a) == classification_semantics(result_b), (result_a, result_b)
        assert classifier_a.name != expected_source, "legacy basename label must not satisfy this regression"

        classifier_b.write_text(CLASSIFIER_TEMPLATE.format(project_type="fixture.changed"), encoding="utf-8")
        changed = pf.classify_project(project, explicit_classifier_paths=[classifier_b])
        assert changed["project_types"] == ["fixture.changed"], changed
        assert changed["project_types"] != result_b["project_types"], (result_b, changed)
        assert changed["matched_rules"][0]["source"] == expected_source, changed

        local_classifier = project / ".pf" / "project-classifiers" / "local.yaml"
        local_classifier.parent.mkdir(parents=True)
        local_classifier.write_text(CLASSIFIER_TEMPLATE.format(project_type="fixture.local"), encoding="utf-8")
        local_result = pf.classify_project(project, explicit_classifier_paths=[local_classifier])
        assert local_result["matched_rules"][0]["source"] == ".pf/project-classifiers/local.yaml", local_result

        workplace = root / "workplace"
        workplace_classifier = workplace / "project-classifiers" / "workplace.yaml"
        workplace_classifier.parent.mkdir(parents=True)
        workplace_classifier.write_text(CLASSIFIER_TEMPLATE.format(project_type="fixture.workplace"), encoding="utf-8")
        manifest = workplace / "workplace.yaml"
        manifest.write_text("schema_version: 1\n", encoding="utf-8")
        registry = workplace / "registries" / "project-classifiers.yaml"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            """schema_version: 1
project_classifiers:
  - id: fixture.workplace.classifier
    path: project-classifiers/workplace.yaml
    status: active
""",
            encoding="utf-8",
        )
        workplace_project = root / "workplace-project"
        workplace_project.mkdir()
        (workplace_project / "app.py").write_text("print('fixture')\n", encoding="utf-8")
        workplace_result = pf.classify_project(workplace_project, workplace_manifest=manifest)
        assert workplace_result["matched_rules"][0]["source"] == "workplace.yaml", workplace_result

    print("PASS: smoke_classifier_distribution_parity")


if __name__ == "__main__":
    main()
