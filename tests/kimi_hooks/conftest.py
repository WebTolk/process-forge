"""Portable actual-host payloads and isolated source ingress fixtures."""

from __future__ import annotations

import copy
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from pf_runtime.codex_hooks import runtime_bootstrap  # noqa: E402
from smoke_conversation_completeness import setup_basic_project  # noqa: E402


@pytest.fixture
def native_payload() -> Callable[..., dict[str, Any]]:
    """Build a fresh payload using inspected Kimi Code producer fields."""
    data = json.loads(
        (Path(__file__).parent / "fixtures/native-hooks.json").read_text(
            encoding="utf-8"
        )
    )

    def build(hook: str, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = copy.deepcopy(data[hook])
        payload.update(overrides)
        return payload

    return build


@pytest.fixture(scope="module")
def source_ingress(tmp_path_factory: Any) -> tuple[Path, Path, Any]:
    """Use a separate file-first workplace, never an existing host session."""
    root = tmp_path_factory.mktemp("kimi-ingress")
    workplace, project = setup_basic_project(root, "project")
    return workplace, project, runtime_bootstrap().core
