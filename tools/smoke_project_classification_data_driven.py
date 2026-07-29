#!/usr/bin/env python3
"""Smoke that project classification changes only with loaded classifier data."""

import tempfile
from pathlib import Path

from smoke_domain_neutral_core_helpers import load_processforge


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
    print("PASS: smoke_project_classification_data_driven")


if __name__ == "__main__":
    main()
