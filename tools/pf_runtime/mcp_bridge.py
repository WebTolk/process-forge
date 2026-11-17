"""Keep host-owned MCP pipes and route Forge requests to its existing Runtime."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import yaml  # type: ignore[import-untyped]

from pf_runtime.mcp_transport import configure_utf8

BACKEND_META = "processforge/backend"


class BackendUnavailable(Exception):
    """The backend did not return a complete, correlated protocol response."""


def _read_mapping(path: Path, *, yaml_document: bool = False) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise BackendUnavailable()
    try:
        value = yaml.safe_load(raw) if yaml_document else json.loads(raw)
    except (ValueError, yaml.YAMLError) as error:
        raise BackendUnavailable() from error
    if not isinstance(value, dict):
        raise BackendUnavailable()
    return value


def _forge_workplace(workplace: str) -> bool:
    try:
        manifest = _read_mapping(Path(workplace) / "workplace.yaml", yaml_document=True)
    except FileNotFoundError:
        return False
    coordination = manifest.get("coordination", {})
    if not isinstance(coordination, dict):
        raise BackendUnavailable()
    return bool(coordination.get("director_enabled", False))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def _runtime_exchange(
    line: str, workplace: str, session_id: str, timeout_seconds: float
) -> bytes:
    """Send once to the selected local Runtime; uncertain writes are never replayed."""
    runtime = Path(workplace) / "runtime/pf-runtime"
    state = _read_mapping(runtime / "service.json")
    token = _read_mapping(runtime / "token.json").get("token")
    endpoint = state.get("endpoint")
    instance = state.get("instance_id")
    if (
        state.get("status") != "ready"
        or not isinstance(endpoint, str)
        or not isinstance(instance, str)
        or not instance
        or not isinstance(token, str)
        or not token
        or not token.isascii()
    ):
        raise BackendUnavailable()
    selected = urlsplit(endpoint)
    if (
        selected.scheme != "http"
        or selected.hostname != "127.0.0.1"
        or not selected.port
        or selected.username is not None
        or selected.password is not None
        or selected.path not in {"", "/"}
        or selected.query
        or selected.fragment
    ):
        raise BackendUnavailable()
    payload = json.dumps(
        {
            "request": _request_value(line),
            "session_id": session_id,
            "expected_instance_id": instance,
        },
        ensure_ascii=True,
    ).encode("utf-8")
    request = Request(
        endpoint.rstrip("/") + "/mcp",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    # Local credentials must not enter a proxy or follow a redirect.
    with build_opener(ProxyHandler({}), _NoRedirect()).open(
        request, timeout=timeout_seconds
    ) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise BackendUnavailable()
    try:
        envelope = json.loads(raw)
    except ValueError as error:
        raise BackendUnavailable() from error
    if (
        not isinstance(envelope, dict)
        or envelope.get("instance_id") != instance
        or not isinstance(envelope.get("messages"), list)
    ):
        raise BackendUnavailable()
    return b"\n".join(
        json.dumps(message, ensure_ascii=True).encode("utf-8")
        for message in envelope["messages"]
    )


def _reject_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON value")


def _request_value(line: str) -> Any:
    try:
        return json.loads(line, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return None


def _notification(request: Any) -> bool:
    return (
        isinstance(request, dict)
        and request.get("jsonrpc") == "2.0"
        and isinstance(request.get("method"), str)
        and "id" not in request
    )


def _request_id(request: Any) -> Any:
    value = request.get("id") if isinstance(request, dict) else None
    if value is None or isinstance(value, str):
        return value
    if type(value) in {int, float} and (
        not isinstance(value, float) or math.isfinite(value)
    ):
        return value
    return None


def exchange(
    line: str, workplace: str, session_id: str, timeout_seconds: float = 120.0
) -> list[dict[str, Any]]:
    """Use the sole Forge executor, or the existing operator-owned Garage entry."""
    workplace = str(Path(workplace).expanduser().resolve())
    if _forge_workplace(workplace):
        stdout = _runtime_exchange(line, workplace, session_id, timeout_seconds)
    else:
        stdout = _garage_exchange(line, workplace, session_id, timeout_seconds)
    return _validated_messages(line, stdout)


def _garage_exchange(
    line: str, workplace: str, session_id: str, timeout_seconds: float
) -> bytes:
    entry = Path(__file__).absolute().with_name("mcp_server.py")
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(entry),
            "--workplace",
            workplace,
            "--session",
            session_id,
            "--backend-request",
        ],
        input=(line.rstrip("\r\n") + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode:
        raise BackendUnavailable()
    return completed.stdout


def _validated_messages(line: str, stdout: bytes) -> list[dict[str, Any]]:
    request = _request_value(line)
    messages: list[dict[str, Any]] = []
    responses = 0
    try:
        # Only LF frames messages. Unicode line separators are JSON string data.
        # Stderr is deliberately opaque: its encoding cannot invalidate stdout.
        for raw in stdout.decode("utf-8").split("\n"):
            if not raw.strip():
                continue
            message = json.loads(raw, parse_constant=_reject_constant)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise BackendUnavailable()
            if "id" in message:
                responses += 1
                if (
                    isinstance(message["id"], bool)
                    or message["id"] != _request_id(request)
                    or ("result" in message) == ("error" in message)
                ):
                    raise BackendUnavailable()
            elif not isinstance(message.get("method"), str):
                raise BackendUnavailable()
            messages.append(message)
    except (ValueError, RecursionError) as error:
        raise BackendUnavailable() from error
    if responses != (0 if _notification(request) else 1):
        raise BackendUnavailable()
    return messages


@dataclass
class BridgeState:
    """Remember discovery subscriptions, never domain state or permissions."""

    tools_seen: bool = False
    tools_revision: str | None = None
    resources_seen: bool = False
    resources_revision: str | None = None
    resource_versions: dict[str, str] = field(default_factory=dict)
    subscriptions: set[str] = field(default_factory=set)

    def observe(
        self, request: Any, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Relay catalogue changes after the new backend has answered."""
        notices: list[dict[str, Any]] = []
        response = next((m for m in messages if "id" in m), {})
        result = response.get("result")
        if not isinstance(result, dict):
            return messages
        raw_meta = result.get("_meta")
        meta = raw_meta.get(BACKEND_META) if isinstance(raw_meta, dict) else None
        if isinstance(meta, dict) and meta.get("contract_version") == 1:
            for kind in ("tools", "resources"):
                key = kind + "_revision"
                revision = meta.get(key)
                previous = getattr(self, key)
                if isinstance(revision, str):
                    if getattr(self, kind + "_seen") and previous != revision:
                        notices.append(
                            {
                                "jsonrpc": "2.0",
                                "method": "notifications/" + kind + "/list_changed",
                            }
                        )
                    setattr(self, key, revision)
            versions = meta.get("resource_versions")
            if isinstance(versions, dict):
                for uri, revision in versions.items():
                    if not isinstance(uri, str) or not isinstance(revision, str):
                        continue
                    previous = self.resource_versions.get(uri)
                    if uri in self.subscriptions and previous != revision:
                        notices.append(
                            {
                                "jsonrpc": "2.0",
                                "method": "notifications/resources/updated",
                                "params": {"uri": uri},
                            }
                        )
                    self.resource_versions[uri] = revision
        if isinstance(request, dict) and not result.get("isError"):
            method = request.get("method")
            if method == "tools/list":
                self.tools_seen = True
            elif method == "resources/list":
                self.resources_seen = True
            elif method in {"resources/subscribe", "resources/unsubscribe"}:
                params = request.get("params")
                uri = params.get("uri") if isinstance(params, dict) else None
                if isinstance(uri, str):
                    if method == "resources/subscribe":
                        self.subscriptions.add(uri)
                    else:
                        self.subscriptions.discard(uri)
        return [*notices, *messages]


def _unavailable(request: Any) -> dict[str, Any] | None:
    if _notification(request):
        return None
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": _request_id(request)}
    if isinstance(request, dict) and request.get("method") == "tools/call":
        response["result"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "error": {
                                "code": "mcp_backend_unavailable",
                                "outcome": "unknown",
                                "automatic_retry": False,
                            }
                        }
                    ),
                }
            ],
            "isError": True,
        }
    else:
        response["error"] = {"code": -32603, "message": "backend unavailable"}
    return response


def _reject_malformed(request: Any) -> tuple[bool, dict[str, Any] | None]:
    """Reject fixed protocol shapes without starting or retaining a Core."""
    request_id = _request_id(request)
    if (
        not isinstance(request, dict)
        or request.get("jsonrpc") != "2.0"
        or not isinstance(request.get("method"), str)
        or (request.get("id") is not None and request_id is None)
    ):
        return True, {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32600, "message": "invalid request"},
        }
    params = request.get("params", {})
    valid = isinstance(params, dict)
    if valid and request["method"] == "tools/call":
        valid = isinstance(params.get("name"), str) and isinstance(
            params.get("arguments", {}), dict
        )
    if valid:
        # Catalogues, per-tool schemas and all business authority belong to the
        # fresh backend. A transport shape check cannot accept a domain request.
        return False, None
    if "id" not in request:
        return True, None
    return True, {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32602, "message": "invalid params"},
    }


def _ping(request: Any) -> tuple[bool, dict[str, Any] | None]:
    """Answer transport liveness independently of business Core availability."""
    if not (
        isinstance(request, dict)
        and request.get("jsonrpc") == "2.0"
        and request.get("method") == "ping"
    ):
        return False, None
    request_id = request.get("id")
    if request_id is not None and (
        isinstance(request_id, bool) or _request_id(request) is None
    ):
        return False, None
    params = request.get("params", {})
    valid = (
        isinstance(params, dict)
        and not set(params) - {"_meta"}
        and ("_meta" not in params or isinstance(params["_meta"], dict))
    )
    if "id" not in request:
        return True, None
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if valid:
        response["result"] = {}
    else:
        response["error"] = {"code": -32602, "message": "invalid params"}
    return True, response


def main() -> int:
    """Serve the existing stdio entry without retaining an executing Core."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--workplace", required=True)
    parser.add_argument("--session", default=os.environ.get("PF_MCP_SESSION_ID", ""))
    parser.add_argument("--backend-timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()
    if (
        not math.isfinite(args.backend_timeout_seconds)
        or args.backend_timeout_seconds <= 0
    ):
        parser.error("--backend-timeout-seconds must be finite and positive")
    configure_utf8()
    state = BridgeState()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line, parse_constant=_reject_constant)
        except (ValueError, RecursionError):
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "parse error"},
                    }
                ),
                flush=True,
            )
            continue
        handled, response = _reject_malformed(request)
        if not handled:
            handled, response = _ping(request)
        if handled:
            if response is not None:
                print(json.dumps(response, ensure_ascii=True), flush=True)
            continue
        try:
            messages = state.observe(
                request,
                exchange(
                    line, args.workplace, args.session, args.backend_timeout_seconds
                ),
            )
        except (
            OSError,
            UnicodeError,
            ValueError,
            subprocess.TimeoutExpired,
            BackendUnavailable,
        ):
            response = _unavailable(request)
            messages = [] if response is None else [response]
        for message in messages:
            print(json.dumps(message, ensure_ascii=True), flush=True)
    return 0
