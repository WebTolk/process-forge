"""Declared scopes do not depend on the size or contents of a checkout."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest

from processforge_core.work.scope_conflicts import ScopeConflictService


@pytest.mark.parametrize(
    ("left", "right", "conflict"),
    [
        ("src/**", "src/package/**", True),
        ("orchestration/**", "orchestration/native/**", True),
        ("src/*/a.py", "src/*/b.py", True),
        ("src/**", "tests/**", False),
        ("**/*.py", "**/*.md", False),
        ("**/a.py", "src/*.py", True),
        ("src/a.py", "src/*.py", True),
        ("src/a.py", "src/b.py", False),
        ("[ab]/**", "[cd]/**", True),
    ],
)
def test_scope_validation_never_traverses_the_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    left: str,
    right: str,
    conflict: bool,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("scope validation attempted a repository inventory")

    for method in ("rglob", "glob", "iterdir"):
        monkeypatch.setattr(Path, method, forbidden)
    service = ScopeConflictService(tmp_path / "uncreated-checkout")
    assert service.overlap(left, right)[0] is conflict
    assert service.overlap(right, left)[0] is conflict


def test_existing_file_witness_cannot_become_a_write_permission(tmp_path: Path) -> None:
    masks = [
        "**",
        "**/*.py",
        "**/*.md",
        "src/**",
        "src/*/a.py",
        "src/a.py",
        "[ab]/**",
        "a[bc]*",
        "a?",
        "[[]*",
        "foo[bar",
    ]
    names = [
        "a",
        "ab",
        "ac",
        "src/a.py",
        "src/pkg/a.py",
        "src/pkg/b.py",
        "docs/a.md",
        "a/file",
        "[name",
        "foo[bar",
    ]
    service = ScopeConflictService(tmp_path)
    for left in masks:
        for right in masks:
            if any(
                fnmatch.fnmatch(name, left) and fnmatch.fnmatch(name, right)
                for name in names
            ):
                assert service.overlap(left, right)[0], (left, right)


def test_future_overlap_is_reported_without_claiming_an_existing_file(
    tmp_path: Path,
) -> None:
    assert ScopeConflictService(tmp_path).overlap("src/**", "src/new/**") == (
        True,
        "possible_glob_overlap",
    )
