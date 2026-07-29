#!/usr/bin/env python3
"""Shared helpers for domain-neutral core public smokes."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
DOMAIN_CORE_PROCESS_IDS = {
    "software-feature-development",
    "bug-fix",
    "testing",
    "content-production",
    "documentation-mirror-import",
}
DOMAIN_MARKERS = {
    "php",
    "web",
    "html",
    "css",
    "javascript",
    "node",
    "composer",
    "phpunit",
    "joomla",
    "laravel",
    "seo",
    "music",
    "video",
    "legal",
}


def load_processforge() -> ModuleType:
    spec = importlib.util.spec_from_file_location("processforge_domain_neutral_smoke", ROOT / "tools" / "processforge.py")
    if not spec or not spec.loader:
        raise AssertionError("cannot load tools/processforge.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_pf(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


def yaml_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(item.get("id"))
        for item in value
        if isinstance(item, dict) and item.get("id")
    ]


def assert_no_domain_ids(values: list[str], label: str) -> None:
    violations = [
        value
        for value in values
        if any(marker in value.lower().replace("_", "-").split(".") for marker in DOMAIN_MARKERS)
    ]
    if violations:
        raise AssertionError(f"{label} contains domain ids: {violations}")
