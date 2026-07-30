#!/usr/bin/env python3
"""Smoke explicit domain-pack classifier import without default activation."""

import shutil
import tempfile
from pathlib import Path

from smoke_domain_neutral_core_helpers import ROOT, load_processforge


def main() -> None:
    pf = load_processforge()
    source = ROOT / "packs" / "official" / "software-development" / "project-classifiers" / "software-web.yaml"
    with tempfile.TemporaryDirectory(prefix="pf-domain-pack-import-") as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        (project / "composer.json").write_text("{}\n", encoding="utf-8")
        before = pf.detect_project(project)
        if before["status"] != "unclassified":
            raise AssertionError(before)
        flow = project / ".pf"
        classifier_dir = flow / "project-classifiers"
        classifier_dir.mkdir(parents=True)
        shutil.copyfile(source, classifier_dir / source.name)
        registry_dir = flow / "registries"
        registry_dir.mkdir()
        (registry_dir / "project-classifiers.yaml").write_text(
            f"""schema_version: 1
project_classifiers:
  - id: processforge.official.software-web.classifier
    path: project-classifiers/{source.name}
    status: active
""",
            encoding="utf-8",
        )
        after = pf.detect_project(project)
        if after["status"] != "classified" or after["project_kind"] != ["software.php-composer"]:
            raise AssertionError(after)
    print("PASS: smoke_domain_pack_can_classify_after_install")


if __name__ == "__main__":
    main()
