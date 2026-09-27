"""Read-only classifier provenance probe; writes no files."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workplace-root", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    root = args.core_root.resolve()
    project = args.project_root.resolve()
    workplace = args.workplace_root.resolve()
    sys.path.insert(0, str(root / "src"))
    from processforge_core.bootstrap import bootstrap_runtime

    runtime = bootstrap_runtime(root / "tools" / "pf_runtime" / "mcp_server.py")
    core = runtime.core
    manifest = workplace / "workplace.yaml"
    snapshot = core.load_yaml_document(project / ".pf/contexts/project-context.snapshot.yaml")
    current = core.classify_project(project, workplace_manifest=manifest)
    recorded = snapshot.get("project_classification", {})
    classifiers = [
        {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in core.project_classifier_paths(manifest, project)
    ]
    fields = sorted(
        key for key in recorded.keys() | current.keys()
        if recorded.get(key) != current.get(key)
    )
    print(json.dumps({
        "label": args.label,
        "core_version": core.PROCESSFORGE_VERSION,
        "core_file_sha256": hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
        "core_loaded_from_requested_root": Path(core.__file__).resolve() == root / "tools/processforge.py",
        "snapshot_id": snapshot["snapshot"]["id"],
        "recorded_classification": recorded,
        "current_classification": current,
        "different_fields": fields,
        "classifiers": classifiers,
    }, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
