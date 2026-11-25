"""Test failure classification at the Codex App Server protocol boundary."""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from processforge_core.runtime.codex_catalog import (
    CatalogError,
    describe_codex_driver,
    read_codex_catalog,
    verify_codex_preferences,
)
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy

SERVER = r"""
import json
import sys
import time

case = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    method = request["method"]
    if method == "initialize":
        result = {}
    elif method == "initialized":
        continue
    elif method == "model/list":
        if case == "timeout":
            time.sleep(60)
        if case == "invalid":
            print("invalid frame", flush=True)
            continue
        if case == "closed":
            break
        result = {"data": [], "nextCursor": "same" if case == "loop" else None}
    elif method == "config/read":
        result = {"config": {"model": " "}}
    print(json.dumps({"id": request["id"], "result": result}), flush=True)
"""


def query(case: str, cwd: Path, *, timeout: float = 5) -> dict:
    @contextmanager
    def launch(argv, process_cwd, environment):
        assert argv == [sys.executable, "app-server"]
        with subprocess.Popen(
            [sys.executable, "-B", "-c", SERVER, case],
            cwd=process_cwd,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ) as agent:
            try:
                yield agent
            finally:
                agent.kill()
                agent.wait(timeout=5)

    return read_codex_catalog(
        cwd, {"PF_CODEX_EXECUTABLE": sys.executable}, launch, timeout=timeout
    )


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("closed", "codex_catalog_closed"),
        ("invalid", "codex_catalog_invalid"),
        ("loop", "codex_catalog_pagination_invalid"),
    ],
)
def test_catalog_protocol_failure_has_no_partial_result(tmp_path, case, reason):
    assert query(case, tmp_path) == {"status": "unknown", "reason": reason}


def test_catalog_deadline_terminates_waiting_agent(tmp_path):
    assert query("timeout", tmp_path, timeout=0.4) == {
        "status": "unknown",
        "reason": "codex_catalog_timeout",
    }


def test_effective_configuration_failure_keeps_confirmed_empty_catalog(tmp_path):
    assert query("empty", tmp_path) == {
        "status": "ready",
        "models": [],
        "configured_defaults": {
            "status": "unknown",
            "reason": "codex_profile_unavailable",
        },
    }


def test_explicit_effort_uses_configured_model_and_preserves_case():
    catalog = {
        "status": "ready",
        "models": [
            {
                "model": "recommended",
                "reasoning_efforts": ["ordinary"],
                "is_default": True,
            },
            {
                "model": "configured",
                "reasoning_efforts": ["Ultra-V2"],
                "is_default": False,
            },
        ],
        "configured_defaults": {"status": "ready", "model": "configured"},
    }

    verify_codex_preferences(catalog, "", "Ultra-V2")
    with pytest.raises(CatalogError, match="codex_reasoning_effort_unavailable"):
        verify_codex_preferences(catalog, "", "ultra-v2")
    with pytest.raises(CatalogError, match="codex_reasoning_effort_unavailable"):
        verify_codex_preferences(catalog, "recommended", "Ultra-V2")


@pytest.mark.parametrize(
    ("options", "reason"),
    [
        (None, "codex_reasoning_effort_unknown"),
        ([], "codex_reasoning_effort_unavailable"),
    ],
)
def test_missing_effort_metadata_and_confirmed_unavailable_are_distinct(
    options, reason
):
    catalog = {
        "status": "ready",
        "models": [{"model": "fixture", "reasoning_efforts": options}],
    }

    verify_codex_preferences(catalog, "fixture", "")
    with pytest.raises(CatalogError, match=reason):
        verify_codex_preferences(catalog, "fixture", "selected")


def test_implicit_agent_preferences_need_no_catalog():
    verify_codex_preferences({"status": "unknown"}, "", "")
    with pytest.raises(CatalogError, match="codex_catalog_unknown"):
        verify_codex_preferences({"status": "unknown"}, "fixture", "")


def test_describe_refuses_a_profile_that_depends_on_worker_preferences(tmp_path):
    driver = RuntimeDriverDefinitionPolicy().default_documents()["codex-exec"]
    driver["environment"]["variables"]["CODEX_HOME"] = (
        "{project_root}/profiles/{agent_reasoning_effort}"
    )

    def cannot_launch(*args):
        raise AssertionError("task-specific profile is unknown during describe")

    assert describe_codex_driver(driver, tmp_path, tmp_path, cannot_launch) == {
        "status": "unknown",
        "reason": "codex_profile_unavailable",
    }
