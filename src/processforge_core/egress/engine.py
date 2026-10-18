"""Attempt-owned immutable views and one-shot, durably audited dispatch."""
from __future__ import annotations

import copy
from contextlib import nullcontext
from functools import wraps
import marshal
from dataclasses import dataclass
from pathlib import Path
import secrets
import time
from typing import Callable

from ..work.context import scope_allows
from .contracts import (EgressError, binding_for, bounded_json, digest, encoded, exact,
                        fingerprint, require_v2, validate_policy)
from .policy import decide, _strings
from .storage import Store
from .transport import JsonTransport, PROTOCOL, implementation_id
from .windows import read_source


def audited(operation):
    @wraps(operation)
    def call(self, *args, **kwargs):
        try:
            return operation(self, *args, **kwargs)
        except EgressError as error:
            # A denied operation never sends. Recording its denial is best effort
            # when the mandatory store itself failed; pre-send audit is never optional.
            try:
                with self.store.locked():
                    self.store.audit(self.key, {"event": "operation_failed", "operation": operation.__name__, "reason": error.code})
            except (EgressError, OSError):
                pass
            raise
    return call


@dataclass(frozen=True)
class View:
    id: str
    body: bytes
    checksum: str
    sources: tuple[str, ...]
    tools: tuple[str, ...]
    created: float
    transformations: tuple[str, ...]
    not_after: int | None


@dataclass(frozen=True)
class TrustedTool:
    """Operator code, never imported from a model-supplied module/argv/path.

    Only declared string arguments; credential is a separate keyword argument.
    Every returned field is inside one bounded JSON unit with a trusted label.
    """
    arguments: tuple[str, ...]
    effect: str
    classification: str
    transform: str
    required: bool
    execute: Callable
    credential: str | None = None

    def fingerprint(self):
        if not hasattr(self.execute, "__code__"):
            raise EgressError("tool_qualification_required")
        return fingerprint({"arguments": self.arguments, "effect": self.effect,
                            "classification": self.classification, "transform": self.transform,
                            "required": self.required, "code": digest(marshal.dumps(self.execute.__code__)),
                            "credential_binding": digest((self.credential or "").encode("utf-8"))})


def builtin_tools():
    return {"text-stats": TrustedTool(("text",), "pure", "public", "none", True,
                                     lambda args, credential=None: {"characters": len(args["text"]),
                                                                     "lines": len(args["text"].splitlines())})}


class Session:
    def __init__(self, *, project: Path, contract: dict, stage: str, attempt: int,
                 policy_loader: Callable, authority: Callable, store: Store,
                 transport: JsonTransport, tools=None, allowed_effects=("pure",), diagnostics=None,
                 authority_lock=nullcontext):
        self.project, self.contract = project.resolve(), copy.deepcopy(contract)
        self.binding = require_v2(self.contract)
        if type(attempt) is not int or attempt < 1 or not isinstance(stage, str) or not stage:
            raise EgressError("invalid_binding")
        self.identity = {**contract["identity"], "contract_checksum": contract["contract_checksum"],
                         "stage": stage, "attempt": attempt}
        self.key = fingerprint(self.identity).removeprefix("sha256:")
        self.loader, self.authority, self.store = policy_loader, authority, store
        self.authority_lock = authority_lock
        self.policy = validate_policy(self.loader())
        if binding_for(self.policy) != self.binding or type(transport) is not JsonTransport:
            raise EgressError("invalid_binding")
        self.transport, self.code = transport, implementation_id()
        self.tools = dict(builtin_tools() if tools is None else tools)
        self.tool_fingerprints = {name: tool.fingerprint() for name, tool in self.tools.items()}
        if tools is not None and any(self.policy.get("tool_bindings", {}).get(name) != tool.fingerprint()
                                     for name, tool in self.tools.items()):
            raise EgressError("tool_qualification_required")
        self.effects = frozenset(allowed_effects)
        self.diagnostics = diagnostics
        self.closed, self.views, self.tokens = False, {}, {}
        self.used, self.input_bytes = set(), 0
        self.handles = {secrets.token_hex(16): name for name in self.policy["sources"]}
        self.reverse = {name: handle for handle, name in self.handles.items()}
        with store.locked(), self.authority_lock():
            self._current()
            if store.load(self.key + ".json") is not None:
                raise EgressError("attempt_already_used")
            store.write(self.key + ".json", {"bytes": 0, "disclosures": 0, "closed": False, "receipts": []})
            store.audit(self.key, {"event": "opened", "binding": fingerprint(self.binding), "implementation": self.code})

    def _current(self, sources=(), tools=()):
        if self.closed:
            raise EgressError("invalid_binding")
        qualification = self.store.load("qualification.json", {})
        if qualification.get("implementation") != self.code or qualification.get("status") != "passed":
            raise EgressError("enforcement_unavailable")
        if (self.authority() != self.identity or binding_for(validate_policy(self.loader())) != self.binding
                or implementation_id() != self.code or fingerprint(self.transport.recipient) != fingerprint(self.policy["recipient"])):
            raise EgressError("invalid_binding")
        if self.store.denied(self.binding, sources, tools):
            raise EgressError("authorization_revoked")
        for source in sources:
            if source not in self.policy["sources"] or source in self.policy["denied_sources"]:
                raise EgressError("source_scope_denied")
            if not scope_allows(self.contract["scope"], source, "read"):
                raise EgressError("source_scope_denied")
        for name in tools:
            if name not in self.policy["tools"] or name not in self.tools or self.tools[name].effect not in self.effects:
                raise EgressError("tool_effect_denied")
            effect = self.tools[name].effect
            scope = self.contract["scope"]
            if effect in scope.get("forbidden_actions", []) or (effect != "pure" and effect not in scope.get("allowed_actions", [])):
                raise EgressError("tool_effect_denied")
            if self.tools[name].fingerprint() != self.tool_fingerprints.get(name):
                raise EgressError("tool_qualification_required")

    def _source(self, path):
        # All authorization checks happen before even stat/open of the source.
        self._current((path,))
        raw = read_source(self.project / path, self.binding["limits"]["unit_bytes"])
        self.input_bytes += len(raw)
        if self.input_bytes > self.binding["limits"]["attempt_bytes"]:
            raise EgressError("attempt_budget_exceeded")
        if digest(raw) != self.policy["sources"][path]["checksum"]:
            raise EgressError("source_changed")
        return raw

    def _view(self, items, sources=(), tools=(), transformations=(), not_after=None):
        body = encoded({"protocol": PROTOCOL, "resources": sorted(self.handles),
                        "tools": sorted(set(self.policy["tools"]) & self.tools.keys()), "items": items})
        if len(body) > self.binding["limits"]["envelope_bytes"]:
            raise EgressError("content_budget_exceeded")
        view = View(secrets.token_hex(16), body, digest(body), tuple(sources), tuple(tools),
                    time.monotonic(), tuple(transformations), not_after)
        if len(self.views) >= 128:
            raise EgressError("content_budget_exceeded")
        if sum(len(v.body) for v in self.views.values()) + len(body) > self.binding["limits"]["attempt_bytes"]:
            raise EgressError("content_budget_exceeded")
        self.store.audit(self.key, {"event": "prepared", "view": view.id, "digest": view.checksum,
                                   "transformations": list(transformations),
                                   "sources": [{"path": p, "checksum": self.policy["sources"][p]["checksum"]} for p in sources]})
        self.views[view.id] = view
        return view

    @audited
    def prepare_view(self, handles=None):
        with self.store.locked(), self.authority_lock():
            self._current()
            selected = ([h for h, name in self.handles.items() if self.policy["sources"][name]["initial"]]
                        if handles is None else handles)
            if not isinstance(selected, list) or len(selected) > 128 or len(set(selected)) != len(selected):
                raise EgressError("invalid_binding")
            items, sources, transforms, expiries, input_bytes = [], [], [], [], 0
            for handle in selected:
                if handle not in self.handles:
                    raise EgressError("invalid_binding")
                path = self.handles[handle]
                raw = self._source(path)
                input_bytes += len(raw)
                if input_bytes > self.binding["limits"]["envelope_bytes"]:
                    raise EgressError("content_budget_exceeded")
                decision = decide(raw, self.policy["sources"][path], self.policy)
                items.append({"ref": handle, "status": decision["decision"], "text": decision["text"]})
                sources.append(path)
                transforms.append(decision["decision"])
                if decision["not_after"] is not None:
                    expiries.append(decision["not_after"])
            return self._view(items, sources, transformations=transforms, not_after=min(expiries, default=None))

    def read_resource(self, handle):
        return self.prepare_view([handle])

    @audited
    def invoke_tool(self, name, arguments):
        with self.store.locked(), self.authority_lock():
            self._current(tools=(name,))
            tool = self.tools[name]
            exact(arguments, set(tool.arguments))
            if any(not isinstance(x, str) or len(x.encode("utf-8")) > 65536 for x in arguments.values()):
                raise EgressError("tool_arguments_invalid")
            # No placeholders are dereferenced; arguments are plain values.
            raw_args = encoded(arguments)
            argument_declaration = {"format": "json", "classification": "public", "required": True, "transform": "none"}
            decide(raw_args, argument_declaration, self.policy)
            self.store.audit(self.key, {"event": "tool_authorized", "tool": name, "effect": tool.effect})
            try:
                result = tool.execute(copy.deepcopy(arguments), credential=tool.credential)
            except Exception:
                # Original exception/traceback might contain tool credentials.
                result = {"error": "tool_failed"}
            try:
                raw = encoded(result)
                result = bounded_json(raw, self.binding["limits"]["unit_bytes"], self.binding["limits"]["json_depth"])
            except (ValueError, TypeError, RecursionError) as exc:
                if isinstance(exc, EgressError):
                    raise
                raise EgressError("unsupported_content") from None
            declaration = {"format": "json", "classification": tool.classification,
                           "required": tool.required, "transform": tool.transform}
            # A credential echo remains secret even if a detector does not know its syntax.
            if tool.credential and any(tool.credential in value for value in _strings(result)):
                declaration["classification"] = "credential"
            decision = decide(raw, declaration, self.policy)
            return self._view([{"ref": secrets.token_hex(16), "status": decision["decision"], "text": decision["text"]}],
                              tools=(name,), transformations=(decision["decision"],), not_after=decision["not_after"])

    def _validate_view(self, view):
        if (not isinstance(view, View) or view.id in self.used or self.views.get(view.id) is not view or digest(view.body) != view.checksum
                or time.monotonic() - view.created >= self.binding["limits"]["token_seconds"]
                or view.not_after is not None and time.time() >= view.not_after):
            raise EgressError("invalid_binding")
        self._current(view.sources, view.tools)
        for source in view.sources:
            self._source(source)

    @audited
    def authorize(self, view):
        with self.store.locked(), self.authority_lock():
            self._validate_view(view)
            if len(self.tokens) >= self.binding["limits"]["disclosures"]:
                raise EgressError("attempt_budget_exceeded")
            nonce = secrets.token_hex(32)
            self.store.audit(self.key, {"event": "authorized", "view": view.id, "nonce": nonce,
                                       "binding": fingerprint([self.identity, self.binding, view.checksum])})
            self.tokens[nonce] = (view.id, time.monotonic())
            return nonce

    @audited
    def dispatch(self, view, token):
        with self.store.locked(), self.authority_lock():
            # Consume before any fallible recheck; a failed token is never reusable.
            claim = self.tokens.pop(token, None)
            if claim is None or claim[0] != view.id or time.monotonic() - claim[1] >= self.binding["limits"]["token_seconds"]:
                raise EgressError("invalid_binding")
            self._validate_view(view)
            state = self.store.load(self.key + ".json")
            limits = self.binding["limits"]
            if state["closed"] or state["disclosures"] >= limits["disclosures"] or state["bytes"] + len(view.body) > limits["attempt_bytes"]:
                raise EgressError("attempt_budget_exceeded")
            state["bytes"] += len(view.body)
            state["disclosures"] += 1
            self.used.add(view.id)
            receipt = {"id": secrets.token_hex(16), "view": view.id, "digest": view.checksum,
                       "status": "dispatching", "bytes": len(view.body), "time": int(time.time())}
            state["receipts"].append(receipt)
            # Both writes must be durable BEFORE transport. A crash between these
            # writes conservatively consumes the budget and may record unknown.
            self.store.write(self.key + ".json", state)
            self.store.audit(self.key, {"event": "dispatching", **receipt})
            try:
                response = self.transport.exchange(view.body, limits["unit_bytes"])
                receipt["status"] = "sent"
            except Exception:
                response = None
                receipt["status"] = "delivery_unknown"
            try:
                self.store.write(self.key + ".json", state)
                self.store.audit(self.key, {"event": "receipt", **receipt})
            except (OSError, EgressError):
                # Bytes may have left; never report failed_before_send here.
                raise EgressError("delivery_unknown") from None
            if self.diagnostics:
                try:
                    self.diagnostics({"event": "egress_receipt", "status": receipt["status"]})
                except Exception:
                    pass
            if response is None:
                raise EgressError("delivery_unknown")
            return response

    @audited
    def export_view(self, view):
        with self.store.locked(), self.authority_lock():
            self._validate_view(view)
            # The exact derivative contains no source map, Work slug or raw hash.
            state = self.store.load(self.key + ".json")
            limits = self.binding["limits"]
            if state["closed"] or state["disclosures"] >= limits["disclosures"] or state["bytes"] + len(view.body) > limits["attempt_bytes"]:
                raise EgressError("attempt_budget_exceeded")
            self.used.add(view.id)
            state["bytes"] += len(view.body)
            state["disclosures"] += 1
            state["receipts"].append({"id": secrets.token_hex(16), "view": view.id, "digest": view.checksum,
                                      "status": "exported", "bytes": len(view.body), "time": int(time.time())})
            self.store.write(self.key + ".json", state)
            self.store.audit(self.key, {"event": "exported", "view": view.id, "digest": view.checksum})
            return view.body

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.views.clear()
        self.tokens.clear()
        self.handles.clear()
        self.reverse.clear()
        with self.store.locked():
            state = self.store.load(self.key + ".json")
            state["closed"] = True
            self.store.write(self.key + ".json", state)
            self.store.audit(self.key, {"event": "closed"})

    def run(self, maximum_rounds=16):
        if type(maximum_rounds) is not int or not 1 <= maximum_rounds <= 128:
            raise EgressError("content_budget_exceeded")
        try:
            view = self.prepare_view()
            for _ in range(maximum_rounds):
                raw = self.dispatch(view, self.authorize(view))
                command = bounded_json(raw, self.binding["limits"]["unit_bytes"], self.binding["limits"]["json_depth"])
                if not isinstance(command, dict):
                    raise EgressError("recipient_response_invalid")
                operation = command.get("op")
                if operation == "read":
                    exact(command, {"op", "handle"})
                    if not isinstance(command["handle"], str):
                        raise EgressError("invalid_binding")
                    view = self.read_resource(command["handle"])
                elif operation == "tool":
                    exact(command, {"op", "name", "arguments"})
                    if not isinstance(command["name"], str):
                        raise EgressError("tool_effect_denied")
                    view = self.invoke_tool(command["name"], command["arguments"])
                elif operation == "finish":
                    exact(command, {"op"}, {"text"} if "result" in self.policy else set())
                    result = {"status": "completed", "enforcement": "mediated_session"}
                    if "text" in command:
                        if not isinstance(command["text"], str):
                            raise EgressError("recipient_response_invalid")
                        with self.store.locked(), self.authority_lock():
                            self._current()
                            decision = decide(command["text"].encode("utf-8"), self.policy["result"], self.policy)
                            final_view = self._view([{"ref": secrets.token_hex(16), "status": decision["decision"],
                                                      "text": decision["text"]}], transformations=(decision["decision"],), not_after=decision["not_after"])
                        self.export_view(final_view)
                        result.update(result=decision["text"], result_decision=decision["decision"])
                    result["disclosures"] = self.store.inspect(self.key)["disclosures"]
                    return result
                else:
                    raise EgressError("operation_unsupported")
            raise EgressError("attempt_budget_exceeded")
        finally:
            self.close()
