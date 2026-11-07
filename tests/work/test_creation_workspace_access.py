"""Explicit Work resource requests cross the creation adapters unchanged."""

from __future__ import annotations

import argparse
import copy
import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from processforge_core.work.context import ContextContractError
from processforge_core.work.context_documents import WORKSPACE_ACCESS_KEYS
from processforge_core.work.creation_scope import CreationScopeService

VALID_ACCESS = [
    {},
    {group: [] for group in WORKSPACE_ACCESS_KEYS},
    {
        "knowledge_resources": ["docs.python-practices:pep8"],
        "templates": ["report-template"],
        "tools": ["python-pytest", "python311-ruff"],
        "mcp": ["docs-server"],
    },
    {"tools": ["a" * 256]},
    {"tools": [f"tool-{index}" for index in range(64)]},
]
INVALID_ACCESS = [
    None,
    False,
    [],
    "python-ruff",
    {"knowledge": ["pep8"]},
    {"unknown": []},
    {"tools": None},
    {"tools": {}},
    {"tools": "python-ruff"},
    {"tools": [None]},
    {"tools": [False]},
    {"tools": [1]},
    {"tools": [[]]},
    {"tools": [{}]},
    {"tools": [{"id": "python-ruff"}]},
    {"tools": [{"id": "python-ruff", "command": "python -m ruff"}]},
    {"tools": [{"path_ref": {"registry": "tools", "id": "python-ruff"}}]},
    {"tools": [{"path_ref": {"relative_path": "../escape"}}]},
    {"tools": [""]},
    {"tools": [" "]},
    {"tools": [" python-ruff"]},
    {"tools": ["python-ruff\n"]},
    {"tools": ["python-ruff\r"]},
    {"tools": ["python-ruff\x00"]},
    {"tools": ["*"]},
    {"tools": ["../private"]},
    {"tools": ["C:/private/tool.py"]},
    {"tools": ["c:/private/tool.py"]},
    {"tools": ["C:\\private\\tool.py"]},
    {"tools": ["\\\\server\\private"]},
    {"tools": ["/private/tool.py"]},
    {"tools": ["file:///private/tool.py"]},
    {"tools": ["${TOOLS}/tool"]},
    {"tools": ["python -m ruff"]},
    {"tools": ["python;ruff"]},
    {"tools": ["python..ruff"]},
    {"tools": ["package:"]},
    {"tools": [":resource"]},
    {"tools": ["package:resource:other"]},
    {"tools": ["python-ruff", "python-ruff"]},
]


def scope(access: Any) -> dict[str, Any]:
    return {"schema_version": 1, "assignment": {"workspace_access": access}}


def test_omitted_resources_keep_legacy_scope() -> None:
    declaration = {"schema_version": 1, "assignment": {}}
    validated = CreationScopeService.validate(declaration)
    assert validated == declaration
    assert "workspace_access" not in validated["assignment"]


@pytest.mark.parametrize("access", VALID_ACCESS)
def test_exact_valid_request_and_deep_copy(access: Any, tmp_path: Path) -> None:
    declaration = scope(copy.deepcopy(access))
    original = copy.deepcopy(declaration)
    validated = CreationScopeService.validate(declaration)
    service = CreationScopeService(
        tmp_path,
        normalizer=lambda: lambda value: value,
        handoff_reader=lambda: lambda path: path.read_bytes(),
    )
    baseline = {"objective": "explicit resources", "parameters": {"a": []}}
    applied = service.apply(baseline, validated)
    assert applied["workspace_access"] == original["assignment"]["workspace_access"]
    applied["workspace_access"].setdefault("tools", []).append("changed")
    applied["parameters"]["a"].append("changed")
    assert declaration == original
    assert validated == original
    assert baseline == {"objective": "explicit resources", "parameters": {"a": []}}


@pytest.mark.parametrize("access", INVALID_ACCESS)
def test_invalid_resource_requests_fail_before_normalization(access: Any) -> None:
    with pytest.raises(ContextContractError, match="work_scope_invalid"):
        CreationScopeService.validate(scope(access))


@pytest.mark.parametrize("group", WORKSPACE_ACCESS_KEYS)
@pytest.mark.parametrize("items", [["a" * 257], [f"tool-{i}" for i in range(65)]])
def test_bounds_apply_to_every_group(group: str, items: list[str]) -> None:
    with pytest.raises(ContextContractError, match="work_scope_invalid"):
        CreationScopeService.validate(scope({group: items}))


@pytest.mark.parametrize("access", VALID_ACCESS + INVALID_ACCESS)
def test_advertised_schema_and_mcp_dispatch_agree(
    access: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pf_runtime import mcp_server, session_read

    import processforge_core.composition as composition

    root = Path(__file__).resolve().parents[2]
    validate = runpy.run_path(str(root / "tools/validate-process-forge-schemas.py"))[
        "validate_instance"
    ]
    advertised = mcp_server.tool_schema("pf.work.start")["properties"]["scope_intent"]
    errors = validate(scope(access), advertised, advertised, "$")
    calls: list[dict[str, Any]] = []

    def start(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {"action": "captured"}

    monkeypatch.setattr(
        composition,
        "build_process_execution_service",
        lambda *_args, **_kwargs: SimpleNamespace(start=start),
    )
    runtime = SimpleNamespace(
        host=SimpleNamespace(resolve_project=lambda _value, _core: tmp_path),
        core=object(),
    )
    arguments = {
        "project_root": str(tmp_path),
        "objective": "explicit resources",
        "scope_intent": scope(access),
    }
    if errors:
        with pytest.raises(session_read.SessionReadError):
            mcp_server._tool_result("pf.work.start", arguments, tmp_path, "", runtime)
        assert calls == []
    else:
        assert mcp_server._tool_result(
            "pf.work.start", arguments, tmp_path, "", runtime
        ) == {"action": "captured"}
        assert calls[0]["scope_intent"] == scope(access)


def test_schema_declares_exact_bounds_for_every_group() -> None:
    from pf_runtime import mcp_server

    access = mcp_server.tool_schema("pf.work.start")["properties"]["scope_intent"][
        "properties"
    ]["assignment"]["properties"]["workspace_access"]
    assert access["additionalProperties"] is False
    assert set(access["properties"]) == set(WORKSPACE_ACCESS_KEYS)
    # The repository's small schema checker does not implement these maxima.
    for group in access["properties"].values():
        assert group["maxItems"] == 64
        assert group["uniqueItems"] is True
        assert group["items"]["maxLength"] == 256
        assert group["items"]["minLength"] == 1


@pytest.mark.parametrize(
    ("access", "accepted"),
    [
        (VALID_ACCESS[2], True),
        ({"tools": "python-ruff"}, False),
        ({"tools": ["C:/private"]}, False),
    ],
)
def test_cli_scope_file_uses_same_validation(
    access: Any,
    accepted: bool,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pf_cli.commands.work import WorkStartCommand

    calls: list[dict[str, Any]] = []

    def start(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {"action": "created_new"}

    scope_file = tmp_path / "scope.json"
    scope_file.write_text(json.dumps(scope(access)), encoding="utf-8")
    command = WorkStartCommand(
        execution_factory=lambda *_args: SimpleNamespace(start=start),
        require_flow_root=lambda project: project / ".pf",
        dump_yaml=lambda document: json.dumps(document),
    )
    status = command.execute(
        argparse.Namespace(
            project_root=str(tmp_path),
            scope_file=str(scope_file),
            objective="explicit resources",
            json=True,
        )
    )
    result = json.loads(capsys.readouterr().out)
    if accepted:
        assert status == 0
        assert calls[0]["scope_intent"] == scope(access)
    else:
        assert status == 1
        assert result["reason"] == "work_scope_invalid"
        assert calls == []


@pytest.mark.parametrize("operation", ["pf.work.search", "pf.work.resolve"])
@pytest.mark.parametrize("selector", ["run_id", "assignment_id", "context_id"])
@pytest.mark.parametrize("value", [None, False, 7, [], {}, "", " ", "../run"])
def test_invalid_work_selectors_block_before_state_read(
    operation: str, selector: str, value: Any, tmp_path: Path
) -> None:
    from pf_runtime import mcp_server

    def unexpected_state_read(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Invalid selectors must fail before state is read")

    runtime = SimpleNamespace(
        host=SimpleNamespace(resolve_project=lambda _value, _core: tmp_path),
        core=SimpleNamespace(locate_flow_root=unexpected_state_read),
    )
    arguments = {
        "project_root": str(tmp_path),
        "run_id": "run",
        "assignment_id": "assignment",
        "context_id": "context",
        selector: value,
    }
    result = mcp_server._tool_result(operation, arguments, tmp_path, "", runtime)
    assert result["status"] == "blocked"
    assert result["reason"] == "work_selector_required"


@pytest.mark.parametrize("operation", ["pf.work.search", "pf.work.resolve"])
def test_missing_work_selectors_do_not_infer_active_work(
    operation: str, tmp_path: Path
) -> None:
    from pf_runtime import mcp_server

    runtime = SimpleNamespace(
        host=SimpleNamespace(resolve_project=lambda _value, _core: tmp_path),
        core=object(),
    )
    result = mcp_server._tool_result(
        operation, {"project_root": str(tmp_path)}, tmp_path, "", runtime
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "work_selector_required"


@pytest.mark.parametrize("exit_code", [None, 7, "public_error"])
def test_system_exit_keeps_tool_error_envelope(
    exit_code: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pf_runtime import mcp_server

    def exit_tool(*_args: Any, **_kwargs: Any) -> Any:
        raise SystemExit(exit_code)

    monkeypatch.setattr(mcp_server, "tool_result", exit_tool)
    response = mcp_server.respond_valid(
        {
            "jsonrpc": "2.0",
            "id": "request",
            "method": "tools/call",
            "params": {"name": "pf.context", "arguments": {}},
        },
        tmp_path,
        "",
        object(),
    )
    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "request"
    assert response["result"]["isError"] is True
    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert json.loads(content[0]["text"]) == {"error": {"code": exit_code}}


@pytest.mark.parametrize(
    "params",
    [
        None,
        [],
        False,
        {"name": "pf.context", "arguments": None},
        {"name": "pf.context", "arguments": []},
        {"name": "pf.context", "arguments": False},
    ],
)
def test_invalid_tool_params_keep_rpc_error_before_dispatch(
    params: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pf_runtime import mcp_server

    def unexpected_dispatch(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Malformed public params must not reach tool dispatch")

    monkeypatch.setattr(mcp_server, "tool_result", unexpected_dispatch)
    response = mcp_server._respond(
        {"jsonrpc": "2.0", "id": "request", "method": "tools/call", "params": params},
        tmp_path,
        "",
        object(),
    )
    assert response == {
        "jsonrpc": "2.0",
        "id": "request",
        "error": {"code": -32602, "message": "invalid params"},
    }
