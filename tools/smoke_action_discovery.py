#!/usr/bin/env python3
"""Focused discovery characterization: registrations, refusal and no execution."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import processforge as pf
from pf_cli.commands.agent_actions import ActionsCommand
from pf_cli.parsers.agent_actions import ActionsCommandParser
from pf_runtime import mcp_server
from pf_runtime.action_catalog import catalog_payload, cli_descriptors, mcp_descriptors, work_facts
from processforge_core.operations.catalogue import ActionCatalog, ActionDescriptor, WorkFacts


def metadata_parity() -> dict[str, int]:
    parser = pf.build_parser()
    rows = {item.action_id: item.detail_payload() for item in cli_descriptors(parser)}
    expected = {}

    def walk(current, path, inherited):
        arguments = inherited + [(path, action) for action in current._actions if not isinstance(action, argparse._SubParsersAction)]
        if path and callable(current.get_default("func")):
            expected["cli:" + " ".join(path)] = arguments
        for action in current._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    walk(child, path + (name,), arguments)

    walk(parser, (), [])
    assert rows.keys() == expected.keys()
    assert json.dumps(str(ROOT))[1:-1] not in json.dumps(rows), "catalogue disclosed the distribution's absolute root"
    for action_id, original in expected.items():
        projected = rows[action_id]["contract"]["arguments"]
        assert len(projected) == len(original)
        for found, (path, native) in zip(projected, original):
            assert found["scope"] == list(path)
            assert found["option_strings"] == native.option_strings
            assert found["dest"] == native.dest and found["required"] == native.required
            assert found["nargs"] == native.nargs
            if "choices" in found:
                assert found["choices"] == list(native.choices)
            if "default" in found:
                assert found["default"] == native.default
    assert "cli:runtime-driver list" in rows and "cli:runtime-driver-list" in rows
    assert "cli:worker-run status" in rows and "cli:worker-run-status" in rows
    assert rows["cli:worker-run status"]["side_effects"]["read_only"] is False
    assert rows["cli:worker-run-status"]["side_effects"]["read_only"] is False
    # All aliases of nested argparse parsers remain actual full routes.
    related = {"cli:runtime serve", "cli:runtime run", "cli:server serve", "cli:server run"}
    for action_id in related:
        assert set(rows[action_id]["aliases"]) == related - {action_id}
    mcp = {item.name: item.detail_payload() for item in mcp_descriptors()}
    assert mcp.keys() == mcp_server.TOOLS.keys()
    for name, item in mcp.items():
        assert item["contract"]["inputSchema"] == mcp_server.tool_schema(name)
        assert item["contract"]["annotations"] == mcp_server.tool_annotations(name)
        assert item["summary"] == mcp_server.TOOLS[name]
    assert mcp_server._RUNTIME_BOOTSTRAP is None, "discovery bootstrapped Runtime"
    return {"cli_actions": len(rows), "mcp_actions": len(mcp)}


def synthetic_parser() -> argparse.ArgumentParser:
    def forbidden(*args, **kwargs):
        raise AssertionError("discovery invoked a handler or converter")

    class Opaque:
        def __call__(self, value):
            return forbidden(value)

        def __str__(self):
            return forbidden()

    parser = argparse.ArgumentParser()
    parser.add_argument("--private-path", default=Path("/private/path"))
    # public-cleanliness: allow-private-path-fixture -- exercise private default suppression.
    parser.add_argument("--raw-path", default="C:\\private\\path")
    parser.add_argument("--api-token", default="do-not-publish")
    parser.add_argument("--opaque", default=Opaque())
    parser.add_argument("--opaque-string", default="also-do-not-publish")
    parser.add_argument("--opaque-list", default=["list-do-not-publish"])
    sub = parser.add_subparsers()
    parent = sub.add_parser("overview", help="Parent with a default handler")
    parent.set_defaults(func=forbidden)
    children = parent.add_subparsers(required=False)
    child = children.add_parser("show", aliases=["ls"], help="Actual aliases")
    child.add_argument("-n", "--number", type=int, choices=[1, 2, 3], default=2)
    child.add_argument("--include", action="append", nargs="+", default=[])
    child.add_argument("--converted", type=Opaque())
    child.add_argument("--optional", nargs="?", choices=["auto", "manual"], const="auto", default="manual")
    group = child.add_mutually_exclusive_group(required=True)
    group.add_argument("--one", action="store_true")
    group.add_argument("--two", action="store_false")
    child.set_defaults(func=forbidden)
    return parser


def metadata_privacy_and_isolation() -> None:
    rows = cli_descriptors(synthetic_parser())
    catalogue = ActionCatalog(rows, version="test")
    parent = catalogue.query(operation="describe", action_id="cli:overview")["action"]
    assert parent["contract"]["invocable_without_subcommand"] is True
    assert parent["contract"]["child_commands"] == ["show", "ls"]
    found = catalogue.query(operation="describe", action_id="cli:overview show")["action"]
    arguments = {item["dest"]: item for item in found["contract"]["arguments"]}
    assert arguments["number"]["option_strings"] == ["-n", "--number"]
    assert arguments["number"]["default"] == 2 and arguments["number"]["value_type"] == "integer"
    assert arguments["include"]["collection"] and arguments["include"]["repeatable"]
    assert arguments["include"]["values_per_occurrence"] == {"minimum": 1, "maximum": None}
    assert arguments["converted"]["value_type"] == "native"
    assert arguments["optional"]["const"] == "auto"
    assert found["contract"]["mutually_exclusive_groups"][0]["required"]
    text = json.dumps(found)
    for private in ("do-not-publish", "private/path", "private\\\\path", "also-do-not-publish", "list-do-not-publish"):
        assert private not in text
    for key in ("private_path", "raw_path", "api_token", "opaque", "opaque_string", "opaque_list"):
        assert "default" not in arguments[key] and "default_omitted" in arguments[key]
    before = catalogue.query(operation="describe", action_id="cli:overview show")
    before["action"]["contract"]["arguments"].clear()
    before["provenance"]["version"] = "modified"
    after = catalogue.query(operation="describe", action_id="cli:overview show")
    assert after["action"]["contract"]["arguments"] and after["provenance"]["version"] == "test"
    original = deepcopy(mcp_server.tool_schema("pf.work.start"))
    mcp = ActionCatalog(mcp_descriptors(), version="test")
    mcp.query(operation="describe", action_id="mcp:pf.work.start")["action"]["contract"]["inputSchema"]["properties"].clear()
    assert mcp_server.tool_schema("pf.work.start") == original
    assert mcp.query(operation="describe", action_id="mcp:pf.work.start")["action"]["contract"]["inputSchema"] == original


def requests_and_provenance() -> None:
    catalogue = ActionCatalog(cli_descriptors(synthetic_parser()), version="test-version")
    first = catalogue.query(operation="list", limit=1)
    second = catalogue.query(operation="list", limit=1, offset=1)
    assert first["returned"] == 1 and first["has_more"] and first["next_offset"] == 1
    assert first["actions"][0]["action_id"] != second["actions"][0]["action_id"]
    assert "contract" not in first["actions"][0], "list returned full contracts"
    assert catalogue.query(operation="list", query="OVERVIEW SHOW")["returned"] == 1
    assert catalogue.query(operation="list", surface="mcp")["total"] == 0
    assert catalogue.query(operation="list", offset=100000)["returned"] == 0
    unknown = catalogue.query(operation="describe", action_id="cli:missing-command")
    assert unknown["status"] == "unsupported" and unknown["action_id"] == "cli:missing-command"
    assert "action" not in unknown
    assert first["provenance"] == second["provenance"]
    assert first["provenance"]["installed_build"] == first["provenance"]["connected_host_build"] == "unknown"
    assert first["provenance"]["version"] == "test-version"
    altered = ActionCatalog((*cli_descriptors(synthetic_parser()), ActionDescriptor("cli:new", "cli", "new", "new", "{}")), version="test-version")
    assert first["provenance"]["catalogue_fingerprint"] != altered.query(operation="list")["provenance"]["catalogue_fingerprint"]

    def forbidden_parser():
        raise AssertionError("invalid request reached parser construction")

    for patch in ({"operation": "execute"}, {"operation": []}, {"surface": "shell"}, {"surface": []},
                  {"limit": 0}, {"limit": 101}, {"limit": True}, {"offset": -1}, {"offset": False},
                  {"query": "q" * 257}, {"operation": "describe", "action_id": ""}):
        request = {"operation": "list", **patch}
        assert catalog_payload(forbidden_parser, version="test", **request)["status"] == "blocked"
    try:
        catalog_payload(forbidden_parser, operation="list", version="test", arbitrary_command="forbidden")
    except TypeError:
        pass
    else:
        raise AssertionError("unknown adapter argument was accepted")
    state = {"action": "work_ready", "context": {"validation": {"status": "valid", "private": "/private/path"}},
             "execution_readiness": {"status": "ready"}, "private": "never published"}
    ready = catalogue.query(operation="list", work=work_facts(state))
    assert ready["work_context"]["execution_readiness"] == "ready"
    assert ready["actions"][0]["permission"]["status"] == "unknown"
    assert ready["actions"][0]["availability"]["status"] == "unknown"
    assert "/private/path" not in json.dumps(ready) and "never published" not in json.dumps(ready)
    blocked = catalogue.query(operation="list", work=WorkFacts("explicit", "blocked", "blocked", "work_blocked", True))
    assert blocked["work_context"]["blockers_present"] and blocked["actions"][0]["permission"]["status"] == "unknown"


def exact_cli_work_selection() -> None:
    calls = []
    state = {"run": {"id": "r"}, "assignment": {"id": "a"}, "context": {"id": "c", "validation": {"status": "valid"}},
             "execution_readiness": {"status": "ready"}, "action": "work_ready"}

    class Native:
        def state(self, **selectors):
            calls.append(selectors)
            return deepcopy(state)

    command = ActionsCommand(parser_factory=synthetic_parser, execution_factory=lambda *_: Native(),
                             require_flow_root=lambda path: calls.append("flow"), dump_yaml=lambda payload: json.dumps(payload), version="test")
    parser = argparse.ArgumentParser()
    ActionsCommandParser(execute=command.execute).register(parser.add_subparsers(required=True).add_parser)

    def execute(argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = command.execute(parser.parse_args(argv + ["--json"]))
        return code, json.loads(output.getvalue())

    assert execute(["actions", "list"])[0] == 0 and not calls
    assert execute(["actions", "list", "--project-root", "."])[0] == 0 and not calls
    for flags in (["--run", "r"], ["--assignment", "a", "--context-id", "c"],
                  ["--run", "", "--assignment", "a", "--context-id", "c"]):
        assert execute(["actions", "list", *flags])[1]["reason"] == "work_selectors_required"
        assert not calls
    exact = ["--run", "r", "--assignment", "a", "--context-id", "c"]
    assert execute(["actions", "list", *exact])[1]["reason"] == "project_root_required" and not calls
    argv = ["actions", "list", "--project-root", ".", *exact]
    code, ready = execute(argv)
    assert code == 0 and calls == ["flow", {"run_id": "r", "assignment_id": "a", "context_id": "c", "session_id": ""}]
    assert ready["work_context"]["selection"] == "explicit"
    state["execution_readiness"]["status"] = "blocked"
    assert execute(argv)[1]["work_context"]["execution_readiness"] == "blocked", "state was cached"
    state["context"]["validation"]["status"] = "blocked"
    assert execute(argv)[1]["reason"] == "work_context_invalid"
    state["context"]["id"] = "other-context"
    assert execute(argv)[1]["reason"] == "work_context_mismatch"
    for unknown in (["--arbitrary-command", "x"], ["--lim", "1"], ["--limit", "0"], ["--limit", "101"], ["--offset", "-1"], ["--surface", "shell"]):
        with redirect_stderr(io.StringIO()):
            try:
                parser.parse_args(["actions", "list", *unknown])
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError("unknown or invalid CLI argument accepted")


def isolated_core_and_cli() -> None:
    code = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))
from processforge_core.operations.catalogue import ActionCatalog, ActionDescriptor
catalogue = ActionCatalog([ActionDescriptor('test:item', 'cli', 'item', 'item', '{}')], version='test')
assert catalogue.query(operation='describe', action_id='test:item')['status'] == 'ready'
assert 'processforge' not in sys.modules
assert not any(name.startswith(('pf_cli', 'pf_runtime')) for name in sys.modules)
print('PASS: isolated Core')
"""
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    listed = subprocess.run([sys.executable, "-B", "tools/processforge.py", "actions", "list", "--surface", "mcp", "--limit", "1", "--json"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert listed.returncode == 0, listed.stderr
    payload = json.loads(listed.stdout)
    assert payload["returned"] == 1
    assert payload["provenance"]["version"] == pf.CORE_PROPERTIES.loaded.version
    partial = subprocess.run([sys.executable, "-B", "tools/processforge.py", "actions", "list", "--project-root", "missing-project", "--run", "r", "--json"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert partial.returncode == 1 and json.loads(partial.stdout)["reason"] == "work_selectors_required"


def main() -> int:
    counts = metadata_parity()
    metadata_privacy_and_isolation()
    requests_and_provenance()
    exact_cli_work_selection()
    isolated_core_and_cli()
    print(json.dumps({"status": "pass", "checks": ["real_parser_metadata", "advertised_mcp_schema_parity", "aliases_and_parent_handlers",
                                                    "privacy_and_copy_isolation", "bounds_and_unknown_arguments", "explicit_fresh_work_state",
                                                    "no_native_execution", "isolated_core_import", "cli_json"], **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
