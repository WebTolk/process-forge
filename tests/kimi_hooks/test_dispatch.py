"""Fail-closed transport receipts and the real direct hook entry point."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from pf_runtime import kimi_hooks

from processforge_core import diagnostics
from processforge_core.work.consistency import RunTaskInputReader


@pytest.mark.parametrize("routing", ["denied", "quarantined", "ignored"])
@pytest.mark.parametrize("exit_code", [0, 1])
def test_runtime_denial_never_uses_local_fallback(
    monkeypatch: Any,
    native_payload: Callable[..., dict[str, Any]],
    tmp_path: Path,
    routing: str,
    exit_code: int,
) -> None:
    body = {
        "accepted": routing != "quarantined",
        "routing_status": routing,
        "diagnostics": {"adapter": {"reason": "adapter_untrusted"}},
    }
    host = SimpleNamespace(
        hook_configuration=lambda *_: (None, True), ingest_event=Mock()
    )

    def request(*_args: Any) -> int:
        print(json.dumps(body))
        return exit_code

    runtime = SimpleNamespace(
        host=host,
        core=SimpleNamespace(resolve_workplace_root=lambda *_args, **_kwargs: tmp_path),
        service=SimpleNamespace(runtime_request=request),
    )
    monkeypatch.setattr(kimi_hooks, "runtime_bootstrap", lambda: runtime)
    monkeypatch.setattr(RunTaskInputReader, "require_flow_root", lambda *_: tmp_path)
    result = kimi_hooks.dispatch(native_payload("SessionStart", cwd=str(tmp_path)))
    assert result["status"] == (
        "ignored" if routing == "ignored" and exit_code == 0 else "denied"
    )
    assert result["diagnostics"] == body["diagnostics"]
    assert result["transport"] == "runtime"
    host.ingest_event.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {"status": "ok"},
        {"routing_status": "routed"},
        {"routing_status": "raw_accepted"},
        {"routing_status": "duplicate_raw"},
        {"accepted": True, "routing_status": "captured"},
    ],
)
def test_empty_http_success_is_not_hook_acceptance(body: Any) -> None:
    with pytest.raises(ValueError):
        kimi_hooks._delivery_result(body, "runtime")


def test_receipt_preserves_accepted_effects() -> None:
    receipt = {
        "accepted": True,
        "routing_status": "routed",
        "normalized_event_ids": ["event-one"],
        "chat_message_ids": ["message-one"],
    }
    result = kimi_hooks._delivery_result(receipt, "runtime")
    assert result["status"] == "delivered"
    assert result["normalized_event_ids"] == receipt["normalized_event_ids"]
    assert result["chat_message_ids"] == receipt["chat_message_ids"]


def test_unavailable_runtime_uses_existing_file_first_fallback(
    monkeypatch: Any, native_payload: Callable[..., dict[str, Any]], tmp_path: Path
) -> None:
    receipt = {
        "accepted": True,
        "routing_status": "routed",
        "normalized_event_ids": ["one"],
    }
    ingest = Mock(return_value=receipt)
    runtime = SimpleNamespace(
        host=SimpleNamespace(
            hook_configuration=lambda *_: (None, True), ingest_event=ingest
        ),
        core=SimpleNamespace(resolve_workplace_root=lambda *_args, **_kwargs: tmp_path),
        service=SimpleNamespace(
            runtime_request=Mock(side_effect=SystemExit("runtime is not running"))
        ),
    )
    monkeypatch.setattr(kimi_hooks, "runtime_bootstrap", lambda: runtime)
    monkeypatch.setattr(RunTaskInputReader, "require_flow_root", lambda *_: tmp_path)
    result = kimi_hooks.dispatch(native_payload("SessionStart", cwd=str(tmp_path)))
    assert result["status"] == "delivered"
    assert result["transport"] == "ledger-fallback"
    assert result["normalized_event_ids"] == ["one"]
    ingest.assert_called_once()


def test_http_success_with_invalid_receipt_does_not_bypass_runtime(
    monkeypatch: Any, native_payload: Callable[..., dict[str, Any]], tmp_path: Path
) -> None:
    ingest = Mock()

    def request(*_args: Any) -> int:
        print("{}")
        return 0

    runtime = SimpleNamespace(
        host=SimpleNamespace(
            hook_configuration=lambda *_: (None, True), ingest_event=ingest
        ),
        core=SimpleNamespace(resolve_workplace_root=lambda *_args, **_kwargs: tmp_path),
        service=SimpleNamespace(runtime_request=request),
    )
    monkeypatch.setattr(kimi_hooks, "runtime_bootstrap", lambda: runtime)
    monkeypatch.setattr(RunTaskInputReader, "require_flow_root", lambda *_: tmp_path)
    result = kimi_hooks.dispatch(native_payload("SessionStart", cwd=str(tmp_path)))
    assert result["status"] == "denied"
    assert result["reason"] == "runtime_invalid_receipt"
    ingest.assert_not_called()


@pytest.mark.parametrize("hook", ["SessionStart", "Stop", "SubagentStop"])
def test_main_has_no_codex_specific_context_output(
    monkeypatch: Any,
    capsys: Any,
    native_payload: Callable[..., dict[str, Any]],
    hook: str,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(native_payload(hook))))
    monkeypatch.setattr(kimi_hooks, "dispatch", lambda _: {"status": "delivered"})
    monkeypatch.setattr(
        diagnostics, "for_project", lambda *_args, **_kwargs: diagnostics.NULL
    )
    assert kimi_hooks.main() == 0
    output = capsys.readouterr().out
    assert "hookSpecificOutput" not in output
    assert output == ("{}\n" if hook in {"Stop", "SubagentStop"} else "")


def test_host_failure_does_not_exit_kimi(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    monkeypatch.setattr(
        diagnostics, "for_project", lambda *_args, **_kwargs: diagnostics.NULL
    )

    def failed(_payload: Any) -> Any:
        raise SystemExit("fixture unavailable")

    monkeypatch.setattr(kimi_hooks, "dispatch", failed)
    assert kimi_hooks.main() == 0


def test_hook_can_be_invoked_as_a_script_without_a_pf_project(tmp_path: Path) -> None:
    script = Path(kimi_hooks.__file__).resolve()
    payload = {
        "hook_event_name": "SessionStart",
        "cwd": str(tmp_path),
        "session_id": "fixture",
    }
    result = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=tmp_path,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "ImportError" not in result.stderr
