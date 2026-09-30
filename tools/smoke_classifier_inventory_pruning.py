#!/usr/bin/env python3
"""Classifier inventory prunes flow/ignored/link trees before visiting them."""

import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from smoke_domain_neutral_core_helpers import load_processforge


def marker(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    return path


def guarded_paths(pf, project: Path, forbidden: set[Path]) -> tuple[set[str], set[Path]]:
    visited: set[Path] = set()
    scandir = os.scandir

    def guarded(path):
        current = Path(path)
        assert not any(current == item or current.is_relative_to(item) for item in forbidden), current
        visited.add(current)
        return scandir(path)

    with patch.object(os, "scandir", guarded):
        paths = pf.project_available_paths(project)
    return paths, visited


def check_pruning(pf, root: Path) -> None:
    project = root / "scale"
    product = marker(project, "application/frontend/package.json")
    marker(project, ".pf-copy/composer.json")
    marker(project, "application/.pf/fixture.marker")
    (project / "empty-marker").mkdir()
    ignored = {".git", ".idea", ".serena", "__pycache__", "runtime", "cache"}
    forbidden = {project / ".pf"}
    for name in sorted(ignored):
        marker(project, f"{name}/hidden/package.json")
        marker(project, f"application/{name}/hidden/package.json")
        # Ignored names apply to files too, preserving generic inventory policy.
        marker(project, f"filenames/{name}")
        forbidden.update({project / name, project / "application" / name})
    for index in range(200):
        marker(project, f".pf/artifacts/batch-{index}/fixture/package.json")
    generic = pf.list_project_files(project)
    expected = pf.project_available_paths(project, generic)
    actual, visited = guarded_paths(pf, project, forbidden)
    assert actual == expected, (actual - expected, expected - actual)
    assert visited == {project / relative for relative in (
        ".", "application", "application/frontend", "application/.pf",
        ".pf-copy", "empty-marker", "filenames",
    )}, visited
    assert "empty-marker" in actual and "cache" in actual and "runtime" in actual
    assert "application/.pf/fixture.marker" in actual
    assert ".pf-copy/composer.json" in actual
    assert product in pf.list_classifier_files(project)
    assert any(path.is_relative_to(project / ".pf") for path in generic)
    inventory = pf.list_classifier_files(project)
    assert inventory == sorted(inventory, key=lambda path: path.relative_to(project).as_posix())
    assert not pf.list_classifier_files(root / "absent")
    # The default classification and inactive-hint paths must use the same walk.
    with patch.object(pf, "list_project_files", side_effect=AssertionError("generic traversal")):
        classified = pf.classify_project(project)
        pf.inactive_official_classifier_hints(None, project)
    assert classified["status"] == "unclassified", classified
    product.unlink()
    assert "application/frontend/package.json" not in pf.project_available_paths(project)
    marker(project, "package.json")
    assert "package.json" in pf.project_available_paths(project)


def check_links(pf, root: Path) -> None:
    project = root / "links"
    receipt = marker(project, ".pf/artifacts/package.json")
    marker(project, "application/main.py")
    forbidden = {project / ".pf"}
    created: list[Path] = []
    try:
        for name, target in (("flow-alias", project / ".pf"), ("cycle", project)):
            link = project / name
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                print(f"SKIP: directory symlink unavailable: {exc.__class__.__name__}")
                break
            created.append(link)
            forbidden.add(link)
        file_link = project / "receipt-link.json"
        try:
            file_link.symlink_to(receipt)
        except OSError as exc:
            print(f"SKIP: file symlink unavailable: {exc.__class__.__name__}")
        else:
            created.append(file_link)
        if os.name == "nt":
            for name, target in (("flow-junction", project / ".pf"), ("cycle-junction", project)):
                junction = project / name
                # Creation only: cleanup uses Python on this exact owned link.
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
                    capture_output=True, text=True, timeout=15,
                )
                assert result.returncode == 0, (result.stdout, result.stderr)
                created.append(junction)
                assert junction.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                forbidden.add(junction)
        paths, visited = guarded_paths(pf, project, forbidden)
        assert "application/main.py" in paths
        assert not any(path.endswith("/package.json") for path in paths), paths
        for link in created:
            assert link.name in paths, (link, paths)  # Root directory/file marker policy.
        assert len(visited) == 2, visited
    finally:
        for link in reversed(created):
            assert link.parent == project and project.is_relative_to(root)
            if link.is_symlink():
                link.unlink()
            else:
                assert os.name == "nt" and link.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                assert link.resolve().is_relative_to(root.resolve())
                link.rmdir()


def main() -> None:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-classifier-pruning-") as temporary:
        root = Path(temporary)
        check_pruning(pf, root)
        check_links(pf, root)
    print("PASS: smoke_classifier_inventory_pruning")


if __name__ == "__main__":
    main()
