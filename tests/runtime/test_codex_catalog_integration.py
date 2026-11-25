"""Exercise live Codex discovery from both real runtime-driver describe commands."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from processforge_core.executions.composition import ExecutionStorage
from processforge_core.prepared import retry_publication
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from tests.executions.test_lifecycle import sql_cli_fixture as sql_cli_fixture
from tests.executions.test_repository import isolated_path as isolated_path

ROOT = Path(__file__).resolve().parents[2]

APP_SERVER = r"""
import json
import os
import sys
from pathlib import Path

assert sys.argv[1:] == ["app-server"]
profile = Path(os.environ["CODEX_HOME"])
with (profile / "requests.log").open("a", encoding="utf-8") as calls:
    for line in sys.stdin:
        request = json.loads(line)
        method = request["method"]
        calls.write(method + "\n")
        calls.flush()
        if method == "initialized":
            continue
        params = request.get("params", {})
        data = json.loads((profile / "catalog.json").read_text(encoding="utf-8"))
        if method == "initialize":
            result = {"userAgent": "fixture"}
        elif method == "model/list":
            index = int(params.get("cursor", 0))
            pages = data["pages"]
            result = {
                "data": pages[index],
                "nextCursor": str(index + 1) if index + 1 < len(pages) else None,
            }
        elif method == "config/read":
            assert Path(params["cwd"]) == Path(os.environ.get("EXPECTED_CONFIG_CWD", Path.cwd()))
            result = {"config": data["config"]}
        else:
            raise AssertionError(method)
        sys.stdout.write(json.dumps({"id": request["id"], "result": result}) + "\n")
        sys.stdout.flush()
"""


def model(name: str, efforts: list[str] | None) -> dict[str, object]:
    result = {
        "id": name,
        "model": name,
        "defaultReasoningEffort": "high",
        "description": "private provider detail",
    }
    if efforts is not None:
        result["supportedReasoningEfforts"] = [
            {"reasoningEffort": effort} for effort in efforts
        ]
    return result


@pytest.fixture
def configured_agent(tmp_path: Path) -> tuple[dict[str, str], Path]:
    server = tmp_path / "app_server.py"
    server.write_text(APP_SERVER, encoding="utf-8")
    if os.name == "nt":
        launcher = tmp_path / "codex.cmd"
        launcher.write_text(
            f'@echo off\n"{sys.executable}" -B "%~dp0app_server.py" %*\n',
            encoding="utf-8",
        )
    else:
        launcher = tmp_path / "codex"
        launcher.write_text(
            f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -B "
            f'{shlex.quote(str(server))} "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o700)
    environment = {
        **os.environ,
        "PF_CODEX_EXECUTABLE": str(launcher),
        "CODEX_HOME": str(tmp_path),
    }
    return environment, tmp_path


def catalog(profile: Path, pages: list[list[dict[str, object]]]) -> None:
    document = {
        "pages": pages,
        "config": {
            "model": "model-A",
            "model_reasoning_effort": "ultra-V2",
            "secret": "private-provider-credential",
        },
    }
    (profile / "catalog.json").write_text(json.dumps(document), encoding="utf-8")


def describe(environment: dict[str, str], *arguments: str) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "bin/pf.py"), *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=25,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_live_describe_reads_pages_and_effective_configuration(configured_agent):
    environment, profile = configured_agent
    catalog(
        profile,
        [
            [model("model-A", ["high", "ultra-V2"]), model("model-B", [])],
            [model("model-C", None)],
        ],
    )

    result = describe(
        environment, "runtime-driver", "describe", "--driver", "codex-exec", "--catalog"
    )

    assert "model_catalog:" in result
    assert "- ultra-V2" in result
    assert "model: model-C" in result
    assert "reasoning_effort: ultra-V2" in result
    assert "reasoning_efforts: null" in result
    assert "private-provider-credential" not in result
    assert "private provider detail" not in result
    assert (profile / "requests.log").read_text(encoding="utf-8").splitlines() == [
        "initialize",
        "initialized",
        "model/list",
        "model/list",
        "config/read",
    ]

    catalog(profile, [[model("replacement", ["new-effort"])]])
    updated = describe(
        environment, "runtime-driver-describe", "--driver", "codex-exec", "--catalog"
    )
    assert "model: replacement" in updated
    assert "model: model-B" not in updated
    assert "- new-effort" in updated


def test_static_subdirectory_uses_its_executable_and_project_configuration(
    configured_agent,
):
    environment, profile = configured_agent
    project = profile / "project"
    wrapper_cwd = project / "subdir"
    wrapper_cwd.mkdir(parents=True)
    (project / ".pf").mkdir()
    (project / ".pf/process-forge.yaml").write_text(
        "schema_version: 1\nproject:\n  id: catalog-fixture\n", encoding="utf-8"
    )
    launcher = Path(environment["PF_CODEX_EXECUTABLE"])
    environment["PF_CODEX_EXECUTABLE"] = os.path.relpath(launcher, wrapper_cwd)
    environment["EXPECTED_CONFIG_CWD"] = str(project)
    driver = RuntimeDriverDefinitionPolicy().default_documents()["codex-exec"]
    driver["working_directory"] = "{project_root}/subdir"
    manifest = project / "driver.yaml"
    manifest.write_text(yaml.safe_dump(driver), encoding="utf-8")
    catalog(profile, [[model("model-A", ["high"])]])

    output = describe(
        environment,
        "runtime-driver",
        "describe",
        "--project-root",
        str(project),
        "--driver",
        str(manifest),
        "--catalog",
    )
    assert "status: ready" in output
    assert "model: model-A" in output and "reasoning_effort: ultra-V2" in output


def test_describe_without_catalog_and_other_drivers_do_not_spawn(configured_agent):
    environment, profile = configured_agent

    ordinary = describe(
        environment, "runtime-driver", "describe", "--driver", "codex-exec"
    )
    manual = describe(
        environment, "runtime-driver-describe", "--driver", "manual", "--catalog"
    )

    assert "model_catalog:" not in ordinary
    assert "status: unsupported" in manual
    assert not (profile / "requests.log").exists()


def test_unavailable_agent_has_distinct_status(configured_agent):
    environment, profile = configured_agent
    environment["PF_CODEX_EXECUTABLE"] = str(profile / "missing-codex")

    result = describe(
        environment, "runtime-driver", "describe", "--driver", "codex-exec", "--catalog"
    )

    assert "status: unknown" in result
    assert "reason: codex_catalog_unavailable" in result
    assert "models:" not in result


def test_mcp_describe_passes_through_the_registered_native_action(
    configured_agent, monkeypatch
):
    environment, profile = configured_agent
    catalog(profile, [[model("model-A", []), model("model-C", None)]])
    for key in ("PF_CODEX_EXECUTABLE", "CODEX_HOME"):
        monkeypatch.setenv(key, environment[key])
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    import processforge as core
    from pf_runtime import host, mcp_server

    project = profile / "project"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    (flow / "process-forge.yaml").write_text(
        "schema_version: 1\nproject:\n  id: catalog-fixture\n",
        encoding="utf-8",
    )
    workplace = profile / "workplace"
    workplace.mkdir()
    runtime = SimpleNamespace(
        core=core,
        host=host,
        properties=SimpleNamespace(loaded=SimpleNamespace(version="test")),
    )
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "pf.runtime_driver.describe",
            "arguments": {
                "project_root": str(project),
                "driver": "codex-exec",
                "catalog": True,
            },
        },
    }

    response = mcp_server._respond(request, workplace, "", runtime)

    assert "error" not in response, response
    result = json.loads(response["result"]["content"][0]["text"])
    assert result["status"] == "ready", result
    catalog_result = result["driver"]["model_catalog"]
    assert catalog_result["status"] == "ready"
    assert [
        (item["model"], item["reasoning_efforts"]) for item in catalog_result["models"]
    ] == [("model-A", []), ("model-C", None)]
    assert "private-provider-credential" not in str(result)


def test_retry_replays_exact_intent_after_catalog_pair_returns(
    configured_agent,
    sql_cli_fixture,
    monkeypatch,
    capsys,
):
    import processforge as core

    environment, profile = configured_agent
    for key in ("PF_CODEX_EXECUTABLE", "CODEX_HOME"):
        monkeypatch.setenv(key, environment[key])
    root, _, args, _ = sql_cli_fixture
    args.driver, args.model, args.reasoning_effort = "codex-exec", "model-A", "Ultra-V2"
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    catalog(profile, [[model("model-A", ["Ultra-V2"])]])
    publish = retry_publication.publish_raw_once

    def interrupt_after_intent(project, destination, raw):
        publish(project, destination, raw)
        if destination.name == retry_publication.INTENT:
            raise OSError("fixture interruption after durable retry intent")

    with monkeypatch.context() as patch:
        patch.setattr(retry_publication, "publish_raw_once", interrupt_after_intent)
        with pytest.raises(OSError, match="after durable retry intent"):
            core.command_worker_run_prepare(args)

    paths = core._work_paths.worker_run(root, "run", "task")
    directory = paths["root"] / "attempts/1"
    intent = directory / retry_publication.INTENT
    applied = directory / retry_publication.APPLIED
    assert intent.is_file() and not applied.exists()
    assert not paths["status"].exists()

    def attempt_files():
        return {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}

    before = attempt_files()
    catalog(profile, [[model("model-A", [])]])
    assert core.command_worker_run_prepare(args) == 1
    assert "codex_reasoning_effort_unavailable" in capsys.readouterr().out
    assert attempt_files() == before
    assert not paths["status"].exists() and not paths["command"].exists()

    catalog(profile, [[model("model-A", ["Ultra-V2"])]])
    assert core.command_worker_run_prepare(args) == 0
    assert intent.read_bytes() == before[intent]
    assert applied.is_file()
    assert not directory.with_name("2").exists()
    state = core.load_agent_run_state(root, "run", "task")
    assert state["status"] == "ready" and state["attempt"] == 1


def test_new_ready_codex_attempt_needs_probe_before_start_registration(
    configured_agent,
    sql_cli_fixture,
    monkeypatch,
    capsys,
):
    import processforge as core

    environment, profile = configured_agent
    for key in ("PF_CODEX_EXECUTABLE", "CODEX_HOME"):
        monkeypatch.setenv(key, environment[key])
    root, repository, args, _ = sql_cli_fixture
    args.driver = None
    chosen = argparse.Namespace(**vars(args))
    chosen.driver, chosen.model, chosen.reasoning_effort = (
        "codex-exec",
        "model-A",
        "Ultra-V2",
    )
    catalog(profile, [[model("model-A", ["Ultra-V2"])]])
    probe = core._probe_codex_worker
    registrations = []
    start_observations = []
    expected = []

    def publish_attempt_after_first_observation(*arguments, start):
        if not start:
            return probe(*arguments, start=start)
        start_observations.append(True)
        before = probe(*arguments, start=start)
        if len(start_observations) == 1:
            assert before is None
            assert core.command_worker_run_prepare(chosen) == 0
            record = repository.load_latest("run", "task")
            assert record is not None and record.phase == "prepared"
            expected.append(record)
            catalog(profile, [[model("model-A", [])]])
        return before

    monkeypatch.setattr(
        core, "_probe_codex_worker", publish_attempt_after_first_observation
    )
    monkeypatch.setattr(
        core, "_register_worker_start", lambda *a: registrations.append(a)
    )

    assert core.command_worker_run_start(args) == 1
    assert "codex_reasoning_effort_unavailable" in capsys.readouterr().out
    assert len(start_observations) == 2
    assert registrations == []
    assert repository.load_latest("run", "task") == expected[0]
    paths = core._work_paths.worker_run(root, "run", "task")
    assert not list(paths["root"].glob("attempts/*/native-tree.json"))
