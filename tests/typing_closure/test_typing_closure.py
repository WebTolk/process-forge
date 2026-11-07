"""Behavior boundaries for W70 typing corrections."""

import io
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pf_runtime import monitor
from pf_runtime.provider_adapters import AdapterPolicy, AdapterRegistry

from processforge_core.chat.export import ChatExportService
from processforge_core.chat.writer import ChatTranscriptWriter
from processforge_core.runtime import metrics
from processforge_core.work.worker_assignment import WorkerAssignmentService


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return 4


@pytest.mark.parametrize(
    "provider,adapter",
    [(None, "x"), ("x", None), ([], "x"), ("x", {}), (1, False), ("unknown", "x")],
)
def test_registry_invalid_identity(provider, adapter):
    registry = AdapterRegistry([AdapterPolicy("p", "a")])
    assert registry.resolve({"provider": provider, "adapter": adapter}) is None


def test_registry_exact_policy():
    policy = AdapterPolicy("p", "a")
    assert (
        AdapterRegistry([policy]).resolve({"provider": "p", "adapter": "a"}) is policy
    )


@pytest.mark.parametrize(
    "body", [None, [], "invalid", {}, {"content": "secret", "redaction": "none"}]
)
@pytest.mark.parametrize("include", [False, True])
def test_export_invalid_and_metadata(body, include):
    result = ChatExportService().chat_export_messages(
        [{"message": body}], include_content=include
    )[0]["message"]
    assert result["role"] is None
    assert ("content" in result) is include
    if not include:
        assert result["content_mode"] == "metadata_only"
    else:
        assert result["content"] == (
            body.get("content", "") if isinstance(body, dict) else ""
        )


@pytest.mark.parametrize("body", [None, [], {}, {"content_hash": "h", "role": "user"}])
def test_duplicate_chat_replay_without_append(tmp_path, body):
    from processforge_core.chat.transcripts import ChatTranscriptReader

    path = ChatTranscriptReader(tmp_path).path("session")
    path.parent.mkdir(parents=True)
    prior = {"session_id": "session", "message_id": "m", "message": body}
    path.write_text(json.dumps(prior) + "\n", encoding="utf-8")
    original = path.read_bytes()
    events = Mock()
    writer = ChatTranscriptWriter(events=events)
    returned = writer.append_chat_message(
        tmp_path,
        session_id="session",
        participant_id="user",
        participant_role="operator",
        message_role="user",
        content="ignored",
        message_id="m",
        event_id="e",
    )
    assert returned == (path, prior, {})
    assert path.read_bytes() == original
    assert (
        events.emit_process_event.call_args.kwargs["data"]["message"]["content_mode"]
        == "metadata_only"
    )
    assert not path.with_suffix(path.suffix + ".lock").exists()


@pytest.mark.parametrize("report", [None, [], {}, {"artifact": "expected.md"}])
def test_prompt_expected_report(tmp_path, monkeypatch, report):
    service = WorkerAssignmentService()
    monkeypatch.setattr(
        service, "load", lambda *args: {"run_id": "run", "expected_report": report}
    )
    text = service.render_prompt(tmp_path, "task")
    expected = isinstance(report, dict) and bool(report)
    assert ("expected.md" in text) is expected


@pytest.mark.parametrize(
    "interval", [None, True, "10", 0, 61, float("nan"), 1, 10.5, 60]
)
def test_metrics_interval_semantics(interval):
    snapshot = {
        "schema_version": 1,
        "instance_id": "instance",
        "observed_at": "1970-01-01T00:00:00+00:00",
        "interval_seconds": interval,
        "groups": {
            name: metrics.group(name, dict.fromkeys(fields, 0), set())
            for name, fields in metrics.FIELDS.items()
        },
    }
    result = metrics.project(snapshot, "instance", now=0)
    if type(interval) in (int, float) and 1 <= interval <= 60:
        assert result["interval_seconds"] == interval
    else:
        assert result is None


def test_probe_partial_header_and_body(monkeypatch):
    body = b'{"ready":true}'
    chunks = [
        b"HTTP/1.0 200 OK\r\n",
        b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n",
        body[:3],
        body[3:],
    ]
    conn = Mock()
    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=False)
    conn.recv.side_effect = chunks
    monkeypatch.setattr(
        monitor.socket, "create_connection", lambda *args, **kwargs: conn
    )
    assert monitor.probe_ready("http://127.0.0.1:1234") == (True, "ready")


def test_posix_terminal_restores_on_failure(monkeypatch):
    stream = Terminal()
    calls = []
    previous = [1, 2, 3]
    monkeypatch.setattr(monitor, "os", SimpleNamespace(name="posix", environ={}))
    monkeypatch.setitem(
        sys.modules,
        "termios",
        SimpleNamespace(
            tcgetattr=lambda fd: previous,
            tcsetattr=lambda *args: calls.append(args),
            TCSADRAIN=2,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "tty",
        SimpleNamespace(setcbreak=lambda fd: calls.append(("cbreak", fd))),
    )
    with pytest.raises(RuntimeError), monitor.terminal_mode(stream, stream):
        raise RuntimeError("body fault")
    assert calls == [("cbreak", 4), (4, 2, previous)]
    assert stream.getvalue().endswith("\x1b[?25h\x1b[?1049l")


@pytest.mark.parametrize("value", [b"q", b"Q", b"\x1b", b"\x03", b""])
def test_posix_exit_bytes(monkeypatch, value):
    stream = Terminal()
    monkeypatch.setattr(
        monitor, "os", SimpleNamespace(name="posix", read=lambda *args: value)
    )
    monkeypatch.setattr(monitor.select, "select", lambda *args: ([stream], [], []))
    assert monitor.wait_for_exit(1, stream)


def test_windows_exit_character(monkeypatch):
    monkeypatch.setattr(monitor, "os", SimpleNamespace(name="nt"))
    monkeypatch.setitem(
        sys.modules, "msvcrt", SimpleNamespace(kbhit=lambda: True, getwch=lambda: "Q")
    )
    assert monitor.wait_for_exit(1, io.StringIO())


def test_screen_size_changes():
    stream = io.StringIO()
    screen = monitor.Screen(stream)
    screen.draw(["row"], (20, 10))
    screen.draw(["row"], (20, 10))
    screen.draw(["row"], (30, 10))
    assert stream.getvalue().count("\x1b[2J") == 2
