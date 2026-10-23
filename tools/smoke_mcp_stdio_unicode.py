#!/usr/bin/env python3
"""Check MCP Unicode pipes with an independent filesystem oracle.

The real source main/parser/dispatcher/serializer run with a controlled bootstrap
and tool sink. This is transport characterization, not normal Core, installed,
Runtime, or connected-host qualification. Fixture guards protect test files only;
the existing Core authorization/security checks must also run independently.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import ModuleType, SimpleNamespace


class CheckFailure(Exception):
    """A bounded diagnostic without resolved paths or request bodies."""


class FixtureError(Exception):
    def __init__(self, code: str):
        self.code = code


class BorrowedText:
    """Embedding control with neither a binary buffer nor a callable codec API."""

    reconfigure = None

    def __init__(self, value: str = ""):
        self.text = io.StringIO(value)

    def __iter__(self):
        return iter(self.text)

    def write(self, value: str) -> int:
        return self.text.write(value)

    def flush(self) -> None:
        self.text.flush()

    @property
    def closed(self) -> bool:
        return self.text.closed

    def close(self) -> None:
        self.text.close()

    def getvalue(self) -> str:
        return self.text.getvalue()


def require(condition: bool, label: str) -> None:
    if not condition:
        raise CheckFailure(label)


def inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise CheckFailure("fixture containment") from exc
    return resolved


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stream_settings(stream) -> dict:
    return {name: getattr(stream, name, None) for name in
            ("encoding", "errors", "line_buffering", "write_through", "closed")}


def load_server(server: Path, expected_sha: str):
    streams = (sys.stdin, sys.stdout, sys.stderr)
    before = [stream_settings(stream) for stream in streams]
    raw = server.read_bytes()
    require(digest(raw) == expected_sha, "source changed before load")
    module = ModuleType("unicode_stdio_fixture_server")
    module.__file__ = str(server)
    # Compile the sealed bytes themselves, avoiding a second loader read/race.
    exec(compile(raw, str(server), "exec"), module.__dict__)
    require(all(a is b for a, b in zip(streams, (sys.stdin, sys.stdout, sys.stderr))),
            "import replaced a borrowed stream")
    require(before == [stream_settings(stream) for stream in streams], "import changed stream settings")
    return module, before


def request_for(data: dict) -> dict:
    return {"jsonrpc": "2.0", "id": data["name"], "method": "tools/call", "params": {
        "name": "pf.resolve", "arguments": {"project_root": data["project_root"],
                                            "resource_id": data["relative"]}}}


def controlled_server(module, data: dict, run_root: Path, events: list):
    # safe_tool_error imports session_read but does not use it in these cases.
    # Supply an inert import, never the Host/device bootstrap or optional logger.
    package = ModuleType("pf_runtime")
    package.session_read = ModuleType("pf_runtime.session_read")
    sys.modules["pf_runtime"] = package
    sys.modules["pf_runtime.session_read"] = package.session_read
    runtime = SimpleNamespace(
        core=SimpleNamespace(resolve_workplace_root=Path),
        properties=SimpleNamespace(loaded=SimpleNamespace(version="fixture")),
    )
    module.runtime_bootstrap = lambda: runtime

    def sink(name, arguments, workplace, session, core_runtime):
        relative = arguments.get("resource_id", "")
        if relative in {"error-ascii", "error-unicode"}:
            code = "fixture_error" if relative == "error-ascii" else "ошибка Ё 漢😀"
            events.append({"kind": "error", "code": code})
            raise FixtureError(code)
        if relative == "notify":
            events.append({"kind": "notification"})
            return {"notified": True}
        project = str(arguments.get("project_root", ""))
        row = {"kind": "path", "path": relative, "codepoints": list(map(ord, relative)),
               "project_codepoints": list(map(ord, project)),
               "project_equal": project == data["project_root"],
               "path_equal": relative == data["relative"], "read_ok": False,
               "content_equal": False, "content": None}
        events.append(row)
        target = inside(Path(project) / relative, run_root)
        # Fixture-only isolation, deliberately not a replacement Core policy.
        if not target.is_relative_to(Path(data["project_root"]).resolve()):
            raise FixtureError("fixture_outside_root")
        try:
            row["content"] = target.read_text(encoding="utf-8")
            row["read_ok"] = True
            row["content_equal"] = row["content"] == data["content"]
        except OSError as exc:
            row["read_error"] = type(exc).__name__
        return row

    module.tool_result = sink

    def respond(request, workplace, session, core_runtime):
        if isinstance(request, dict) and request.get("method") == "fixture/internal-error":
            raise RuntimeError("controlled internal error")
        return module._respond(request, workplace, session, core_runtime)

    module.respond = respond
    return runtime


def wire_messages(raw: bytes) -> list:
    require(bool(raw) and raw.endswith(b"\n"), "missing newline-framed output")
    messages = []
    for line in raw.split(b"\n")[:-1]:
        if line.endswith(b"\r"):
            line = line[:-1]
        require(bool(line), "extra blank stdout line")
        messages.append(json.loads(line.decode("utf-8", errors="strict")))
    return messages


def check_path_output(raw: bytes, data: dict) -> None:
    messages = wire_messages(raw)
    require(len(messages) == 1, "unexpected stdout response count")
    response = messages[0]
    require(response.get("id") == data["name"] and "error" not in response, "path RPC error")
    require(not response["result"].get("isError"), "path tool error")
    result = json.loads(response["result"]["content"][0]["text"])
    require(result["codepoints"] == list(map(ord, data["relative"])), "semantic path codepoints")
    require(result["project_codepoints"] == list(map(ord, data["project_root"])),
            "semantic project codepoints")
    require(all(result[key] for key in ("path_equal", "project_equal", "read_ok", "content_equal")),
            "independent fixture read")
    require(result["content"] == data["content"], "fixture content")


def protocol_requests(escaped: bool, data: dict) -> tuple[bytes, list]:
    lines = ["", " \t", "{bad-json", "NaN", "[]"]
    expected = [(None, -32700), (None, -32700), (None, -32600)]

    def add(value: dict, code=None, tool_code=None):
        lines.append(json.dumps(value, ensure_ascii=escaped))
        if "id" in value:
            expected.append((value["id"], code, tool_code))

    add({"jsonrpc": "2.0", "id": "ascii", "method": "initialize"})
    add({"jsonrpc": "2.0", "id": "Юникод Ё 漢😀", "method": "initialize"})
    add({"jsonrpc": "2.0", "id": "params", "method": "initialize", "params": []}, -32602)
    add({"jsonrpc": "2.0", "id": "unknown", "method": "fixture/unknown"}, -32601)
    add({"jsonrpc": "2.0", "id": "internal", "method": "fixture/internal-error"}, -32603)
    for name, code in (("error-ascii", "fixture_error"), ("error-unicode", "ошибка Ё 漢😀")):
        add({"jsonrpc": "2.0", "id": name, "method": "tools/call", "params": {
            "name": "pf.resolve", "arguments": {"resource_id": name}}}, tool_code=code)
    add({"jsonrpc": "2.0", "id": "traversal", "method": "tools/call", "params": {
        "name": "pf.resolve", "arguments": {"project_root": data["project_root"],
                                            "resource_id": "../outside.txt"}}},
        tool_code="fixture_outside_root")
    add({"jsonrpc": "2.0", "id": "wrong-root", "method": "tools/call", "params": {
        "name": "pf.resolve", "arguments": {
            "project_root": str(Path(data["project_root"]).parent / "sibling"),
            "resource_id": data["relative"]}}}, tool_code="fixture_outside_root")
    add({"jsonrpc": "2.0", "id": "invalid-tool", "method": "tools/call", "params": {
        "name": "pf.resolve", "arguments": {"resource_id": False}}}, -32602)
    for method, params in (("initialize", {}), ("notifications/initialized", {}),
                           ("fixture/unknown", {}), ("fixture/internal-error", {}),
                           ("tools/call", {"name": "pf.resolve", "arguments": {"resource_id": "notify"}}),
                           ("tools/call", {"name": "pf.resolve", "arguments": {"resource_id": False}})):
        add({"jsonrpc": "2.0", "method": method, "params": params})
    add({"jsonrpc": "2.0", "id": "sentinel", "method": "initialize"})
    return ("\n".join(lines) + "\n").encode("utf-8"), expected


def check_protocol(raw: bytes, expected: list, audit: dict) -> None:
    messages = wire_messages(raw)
    require(len(messages) == len(expected), "protocol/notification response count")
    for response, spec in zip(messages, expected):
        request_id, code, *rest = spec
        require(response.get("jsonrpc") == "2.0" and response.get("id") == request_id,
                "protocol response identity")
        if code is not None:
            require(response.get("error", {}).get("code") == code, "protocol error contract")
        elif rest and rest[0]:
            require(response["result"].get("isError") is True, "tool error flag")
            text = json.loads(response["result"]["content"][0]["text"])
            require(text == {"error": {"code": rest[0]}}, "ASCII/Unicode tool error content")
        else:
            require("result" in response and "error" not in response, "initialize response")
    events = audit["events"]
    require(sum(row["kind"] == "notification" for row in events) == 1,
            "valid notification dispatch")
    require(sum(row["kind"] == "error" for row in events) == 2, "invalid params reached sink")


def embedding_checks(module, data: dict, events: list) -> int:
    saved = sys.stdin, sys.stdout, sys.stderr, sys.argv
    request = json.dumps(request_for(data), ensure_ascii=False) + "\r\n"
    checks = 0
    try:
        for stream_type in (io.StringIO, BorrowedText):
            incoming, outgoing, errors = stream_type(request), stream_type(), stream_type()
            try:
                sys.stdin, sys.stdout, sys.stderr = incoming, outgoing, errors
                sys.argv = [module.__file__, "--workplace", data["project_root"]]
                require(module.main() == 0, "embedded main exit")
                require((sys.stdin is incoming and sys.stdout is outgoing and sys.stderr is errors),
                        "borrowed text stream replaced")
                require(not any(s.closed for s in (incoming, outgoing, errors)), "borrowed text stream closed")
                require(not errors.getvalue(), "embedded stderr")
                check_path_output(outgoing.getvalue().encode("utf-8"), data)
                checks += 1
            finally:
                sys.stdin, sys.stdout, sys.stderr = saved[:3]
                for stream in (incoming, outgoing, errors):
                    stream.close()  # Only the test, which owns these objects, closes them.
        for error_mode, buffering in (("strict", False), ("replace", True), ("surrogateescape", False)):
            input_buffer, output_buffer, error_buffer = io.BytesIO(request.encode("utf-8")), io.BytesIO(), io.BytesIO()
            incoming = io.TextIOWrapper(input_buffer, encoding="cp1251", errors=error_mode, newline="")
            outgoing = io.TextIOWrapper(output_buffer, encoding="cp1251", errors=error_mode,
                                        newline="\r\n", line_buffering=buffering, write_through=not buffering)
            errors = io.TextIOWrapper(error_buffer, encoding="cp1251", errors="backslashreplace")
            try:
                before = [stream_settings(stream) for stream in (incoming, outgoing, errors)]
                sys.stdin, sys.stdout, sys.stderr = incoming, outgoing, errors
                sys.argv = [module.__file__, "--workplace", data["project_root"]]
                require(module.main() == 0, "borrowed wrapper main exit")
                outgoing.flush()
                require(sys.stdin is incoming and sys.stdout is outgoing and sys.stderr is errors,
                        "borrowed wrapper replaced")
                require(not any(s.closed for s in (incoming, outgoing, errors)), "borrowed wrapper closed")
                require(incoming.buffer is input_buffer and outgoing.buffer is output_buffer,
                        "borrowed binary buffer replaced")
                require(incoming.errors == outgoing.errors == error_mode, "existing errors changed")
                require(stream_settings(errors) == before[2] and not error_buffer.getvalue(), "stderr changed")
                require(outgoing.line_buffering == buffering and outgoing.write_through == (not buffering),
                        "buffering changed")
                require(incoming.newlines == "\r\n", "input newline handling")
                require(output_buffer.getvalue().endswith(b"\r\n") and
                        output_buffer.getvalue().count(b"\n") == 1, "output newline handling")
                check_path_output(output_buffer.getvalue(), data)
                checks += 1
            finally:
                sys.stdin, sys.stdout, sys.stderr = saved[:3]
                for stream in (incoming, outgoing, errors):
                    stream.close()
        for codec in ("utf-8", "utf8", "cp65001"):
            input_buffer = io.BytesIO(b"consumed\r\n" + request.encode("utf-8"))
            output_buffer = io.BytesIO()
            incoming = io.TextIOWrapper(input_buffer, encoding=codec, errors="surrogateescape", newline="")
            outgoing = io.TextIOWrapper(output_buffer, encoding=codec, errors="replace", newline="\r\n",
                                        line_buffering=True, write_through=False)
            errors = io.StringIO()
            try:
                require(incoming.readline() == "consumed\r\n", "preread UTF8 control")
                before = [stream_settings(s) for s in (incoming, outgoing, errors)]
                sys.stdin, sys.stdout, sys.stderr = incoming, outgoing, errors
                sys.argv = [module.__file__, "--workplace", data["project_root"]]
                require(module.main() == 0, "preread UTF8 main exit")
                outgoing.flush()
                require(before == [stream_settings(s) for s in (incoming, outgoing, errors)],
                        "already UTF8 borrowed settings changed")
                require(sys.stdin is incoming and sys.stdout is outgoing and sys.stderr is errors,
                        "preread UTF8 streams replaced")
                require(incoming.buffer is input_buffer and outgoing.buffer is output_buffer,
                        "preread UTF8 buffers replaced")
                require(not any(s.closed for s in (incoming, outgoing, errors)), "preread UTF8 stream closed")
                require(not errors.getvalue(), "preread UTF8 stderr")
                check_path_output(output_buffer.getvalue(), data)
                checks += 1
            finally:
                sys.stdin, sys.stdout, sys.stderr = saved[:3]
                for stream in (incoming, outgoing, errors):
                    stream.close()
        incoming = io.TextIOWrapper(io.BytesIO(b"unread input"), encoding="cp1251", errors="replace")
        outgoing = io.TextIOWrapper(io.BytesIO(), encoding="cp1251", errors="replace")
        errors = io.StringIO()
        try:
            before = [stream_settings(s) for s in (incoming, outgoing, errors)]
            sys.stdin, sys.stdout, sys.stderr = incoming, outgoing, errors
            sys.argv = [module.__file__, "--help"]
            original_bootstrap = module.runtime_bootstrap
            module.runtime_bootstrap = lambda: (_ for _ in ()).throw(CheckFailure("help bootstrapped Core"))
            try:
                module.main()
                raise CheckFailure("help did not exit")
            except SystemExit as exc:
                require(exc.code == 0, "help exit")
            finally:
                module.runtime_bootstrap = original_bootstrap
            require(before == [stream_settings(s) for s in (incoming, outgoing, errors)],
                    "help changed stream settings")
            require(sys.stdin is incoming and sys.stdout is outgoing and sys.stderr is errors,
                    "help replaced streams")
            require(incoming.tell() == 0, "help consumed input")
            checks += 1
        finally:
            sys.stdin, sys.stdout, sys.stderr = saved[:3]
            for stream in (incoming, outgoing, errors):
                stream.close()
    finally:
        sys.stdin, sys.stdout, sys.stderr, sys.argv = saved
    return checks


def child(args) -> int:
    run_root = args.fixture.parent.resolve()
    inside(run_root, args.scratch_root)
    inside(args.fixture, run_root)
    inside(args.audit, run_root)
    # Independent explicit UTF8 oracle, never the possibly misdecoded request.
    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    module, before = load_server(args.server, data["module_sha256"])
    events = []
    controlled_server(module, data, run_root, events)
    audit = {"module_sha256": data["module_sha256"], "initial_streams": before, "events": events}
    save_json(args.audit, audit)
    try:
        if args.probe_child == "embedding":
            count = embedding_checks(module, data, events)
            print(json.dumps({"embedding_checks": count}, ensure_ascii=True), flush=True)
            return 0
        sys.argv = [str(args.server), "--workplace", str(run_root)]
        return module.main()
    finally:
        audit["final_streams"] = [stream_settings(s) for s in (sys.stdin, sys.stdout, sys.stderr)]
        save_json(args.audit, audit)


def fixtures(run_root: Path, module_sha: str) -> tuple[list, list]:
    names = [("ascii", "ascii/data.txt"), ("cyrillic", "Кириллица/Ёж е ё.txt"),
             ("mixed-spaces", "mix-Ё/project with  spaces/мой отчёт.txt"),
             ("punctuation", "punct -_.,;()[]{}+=@#%&!$^'/literal %23#$.txt"),
             ("cjk-emoji", "漢字/emoji-😀.txt"), ("nbsp", "a\u00a0b/данные.txt"),
             ("nfc", "normalization/caf\u00e9.txt"), ("nfd", "normalization/cafe\u0301.txt")]
    result, limits = [], []
    for name, relative in names:
        project = run_root / ("project-ascii" if name == "ascii" else "Проект Ё")
        target = inside(project / relative, run_root)
        if name == "nfd" and target.exists():
            nfc = project / "normalization/caf\u00e9.txt"
            if target.samefile(nfc):
                limits.append("filesystem aliases NFC/NFD names; distinct-name case unavailable")
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = name + ": " + ("ASCII" if name == "ascii" else "Ё е ё 漢 😀\u00a0caf\u00e9 cafe\u0301")
        target.write_text(content, encoding="utf-8")
        data = {"name": name, "project_root": str(project), "relative": relative, "content": content,
                "module_sha256": module_sha}
        path = inside(run_root / (name + ".json"), run_root)
        save_json(path, data)
        result.append((data, path))
    return result, limits


def execute(args, run_root: Path, data: dict, fixture: Path, codec: str,
            escaped: bool, mode: str, raw: bytes) -> tuple[dict, bytes, dict]:
    name = data["name"] + "-" + mode + "-" + codec + ("-escaped" if escaped else "-raw")
    audit_path = inside(run_root / (name + ".audit.json"), run_root)
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--source-root", str(args.source_root),
            "--scratch-root", str(args.scratch_root), "--server", str(args.server),
            "--probe-child", mode, "--fixture", str(fixture), "--audit", str(audit_path)]
    # Do not forward unrelated secrets, host hooks or Python startup customization.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "PATHEXT")
           if key in os.environ}
    selected = {"PYTHONUTF8": "0", "PYTHONIOENCODING": codec, "PYTHONDONTWRITEBYTECODE": "1"}
    env.update(selected)
    try:
        completed = subprocess.run(argv, input=raw, capture_output=True, cwd=run_root,
                                   env=env, timeout=30, shell=False)
        stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = exc.stdout or b"", exc.stderr or b"", -1
    for suffix, value in (("request.bin", raw), ("stdout.bin", stdout), ("stderr.bin", stderr)):
        inside(run_root / (name + "." + suffix), run_root).write_bytes(value)
    audit = json.loads(audit_path.read_bytes()) if audit_path.exists() else {}
    receipt = {"case": name, "argv": argv, "selected_env": selected, "exit_code": code,
               "module_sha256": data["module_sha256"], "request_sha256": digest(raw),
               "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr),
               "has_stderr": bool(stderr), "audit": audit, "passed": False}
    return receipt, stdout, audit


def run_checks(args, run_root: Path) -> dict:
    seal = digest(args.server.read_bytes())
    cases, limits = fixtures(run_root, seal)
    receipts, failures = [], []

    def run(data, fixture, codec, escaped, mode, raw, validate):
        receipt, stdout, audit = execute(args, run_root, data, fixture, codec, escaped, mode, raw)
        try:
            require(receipt["exit_code"] == 0 and not receipt["has_stderr"], "child exit/stderr")
            require(audit.get("module_sha256") == seal, "loaded source seal")
            validate(stdout, audit)
            receipt["passed"] = True
        except (CheckFailure, ValueError, KeyError, TypeError, UnicodeError, IndexError) as exc:
            label = str(exc) if isinstance(exc, CheckFailure) else type(exc).__name__
            receipt["failure"] = label
            failures.append(receipt["case"] + ": " + label)
        save_json(inside(run_root / (receipt["case"] + ".receipt.json"), run_root), receipt)
        receipts.append(receipt)

    for data, fixture in cases:
        for codec in ("utf-8", "cp1251"):
            for escaped in (False, True):
                raw = (json.dumps(request_for(data), ensure_ascii=escaped) + "\n").encode("utf-8")
                run(data, fixture, codec, escaped, "path", raw,
                    lambda stdout, audit, expected=data: check_path_output(stdout, expected))
    data, fixture = cases[0]
    for codec in ("utf-8", "cp1251"):
        for escaped in (False, True):
            raw, expected = protocol_requests(escaped, data)
            run(data, fixture, codec, escaped, "protocol", raw,
                lambda stdout, audit, wanted=expected: check_protocol(stdout, wanted, audit))
    data, fixture = next((data, fixture) for data, fixture in cases if data["name"] == "cyrillic")
    run(data, fixture, "cp1251", False, "embedding", b"",
        lambda stdout, audit: require(wire_messages(stdout) == [{"embedding_checks": 9}], "embedding checks"))
    require(digest(args.server.read_bytes()) == seal, "source changed during checks")
    return {"proof_boundary": "controlled source transport fixture only; not normal Core/installed/Runtime/connected",
            "module_sha256": seal, "path_pipe_cases": len(cases) * 4, "protocol_batches": 4,
            "embedding_checks": 9, "subprocesses": len(receipts), "limits": limits,
            "passed": not failures, "failures": failures, "receipts": receipts,
            "unqualified": ["full Core authorization and CLI behavior", "UNC/junction/reserved/long paths",
                            "archive/installed/Runtime/connected host"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--scratch-root", type=Path)
    parser.add_argument("--server", type=Path, help="Optional exact source preimage for a negative control")
    parser.add_argument("--keep-evidence", action="store_true", help="Retain private raw receipts under scratch root")
    parser.add_argument("--probe-child", choices=("path", "protocol", "embedding"), help=argparse.SUPPRESS)
    parser.add_argument("--fixture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--audit", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.source_root = args.source_root.resolve()
    args.server = (args.server or args.source_root / "tools/pf_runtime/mcp_server.py").resolve()
    args.scratch_root = (args.scratch_root or args.source_root / ".pf/tmp/mcp-stdio-unicode-check").resolve()
    if args.probe_child:
        return child(args)
    run_root = None
    passed = False
    try:
        require(args.server.is_file(), "server source unavailable")
        args.scratch_root.mkdir(parents=True, exist_ok=True)
        # Exclusive creation with inherited directory access. Python's 0700
        # tempfile directory ACL can prevent a sandbox child from using it on
        # Windows; do not change machine ACLs or reuse an existing directory.
        run_root = inside(args.scratch_root / ("run-" + uuid.uuid4().hex), args.scratch_root)
        run_root.mkdir(exist_ok=False)
        result = run_checks(args, run_root)
        save_json(inside(run_root / "result.json", run_root), result)
        passed = result["passed"]
        if not passed:
            print("FAIL: MCP Unicode stdio: " + result["failures"][0], file=sys.stderr)
            return 1
        limitations = "; " + "; ".join(result["limits"]) if result["limits"] else ""
        print(f"PASS: MCP Unicode stdio; {result['path_pipe_cases']} path/pipe cases, "
              f"4 protocol batches, {result['embedding_checks']} embedding checks; controlled transport fixture only{limitations}")
        return 0
    except (CheckFailure, OSError, ValueError) as exc:
        if run_root is not None:
            try:
                save_json(inside(run_root / "failure.json", run_root), {"type": type(exc).__name__})
            except OSError:
                pass  # The original failure still returns nonzero below.
        label = str(exc) if isinstance(exc, CheckFailure) else type(exc).__name__
        print("FAIL: MCP Unicode stdio: " + label, file=sys.stderr)
        return 1
    finally:
        if passed and not args.keep_evidence and run_root is not None:
            target = inside(run_root, args.scratch_root)
            require(target != args.scratch_root and target.parent == args.scratch_root,
                    "scratch cleanup boundary")
            shutil.rmtree(target)


if __name__ == "__main__":
    raise SystemExit(main())
