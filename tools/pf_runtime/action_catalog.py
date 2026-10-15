"""Read actual CLI and MCP registrations into data-only Core descriptors.

argparse inspection deliberately lives in this adapter. Building a catalogue
never parses caller argv, invokes a handler, loads a project or starts Runtime.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import replace
import json
import math
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any

from processforge_core.operations.catalogue import ActionCatalog, ActionDescriptor, CatalogRequestError, WorkFacts


_OMITTED = object()
_SENSITIVE = re.compile(r"password|passwd|secret|token|credential|authorization|api[_-]?key|environment", re.I)
_ABSOLUTE_TEXT = re.compile(r"[A-Za-z]:[\\/]|(?:^|[\s'\"(=])(?:/[^\s/]|\\\\)|file://")


def _public_text(value: Any) -> str:
    if not isinstance(value, str) or value == argparse.SUPPRESS:
        return ""
    if _ABSOLUTE_TEXT.search(value):
        return "Native documentation contains a path omitted from discovery."
    return value[:4096]


def _portable(value: Any) -> Any:
    """Never stringify objects, paths, callbacks or private runtime values."""
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else _OMITTED
    if type(value) is str:
        if (len(value) > 256 or value == argparse.SUPPRESS or "\n" in value or "\r" in value
                or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
                or value.startswith(("\\", "~", "file:")) or "://" in value):
            return _OMITTED
        return value
    if type(value) in (list, tuple) and len(value) <= 128:
        values = [_portable(item) for item in value]
        return _OMITTED if any(item is _OMITTED for item in values) else values
    if type(value) is dict and not value:
        return {}
    return _OMITTED


def _argument(action: argparse.Action, path: tuple[str, ...]) -> dict[str, Any]:
    names = {
        argparse._StoreAction: "store", argparse._StoreTrueAction: "store_true",
        argparse._StoreFalseAction: "store_false", argparse._StoreConstAction: "store_const",
        argparse._AppendAction: "append", argparse._AppendConstAction: "append_const",
        argparse._CountAction: "count", argparse._ExtendAction: "extend", argparse._HelpAction: "help",
        argparse._VersionAction: "version", argparse.BooleanOptionalAction: "boolean_optional",
    }
    action_kind = names.get(type(action), "native")
    nargs = action.nargs
    if nargs is None:
        minimum, maximum = 1, 1
    elif type(nargs) is int:
        minimum = maximum = nargs
    else:
        minimum, maximum = {"?": (0, 1), "*": (0, None), "+": (1, None), argparse.REMAINDER: (0, None)}.get(nargs, (None, None))
    value_type = next((label for converter, label in ((None, "string"), (str, "string"), (int, "integer"), (float, "number"))
                       if action.type is converter), "native")
    if nargs == 0:
        value_type = "none"
    result: dict[str, Any] = {
        "scope": list(path), "dest": action.dest, "option_strings": list(action.option_strings),
        "positional": not bool(action.option_strings), "required": bool(action.required),
        "action": action_kind, "nargs": nargs, "value_type": value_type,
        "values_per_occurrence": {"minimum": minimum, "maximum": maximum},
        "repeatable": action_kind in {"append", "append_const", "extend", "count"},
        "collection": action_kind in {"append", "append_const", "extend"} or (nargs is not None and nargs != "?" and nargs != 0),
        "help": _public_text(action.help), "native_validation_required": True,
    }
    sensitive = bool(_SENSITIVE.search(action.dest + " " + " ".join(action.option_strings)))
    choices = _portable(list(action.choices)) if action.choices is not None and not sensitive else _OMITTED
    if choices is not _OMITTED:
        result["choices"] = choices
    elif action.choices is not None:
        result["choices_omitted"] = "private_or_nonportable"
    default = _portable(action.default) if not sensitive else _OMITTED
    # Nonempty strings are published only when declared as portable choices.
    # Other native strings may be private defaults even without a telling name.
    if isinstance(default, str) and default and (choices is _OMITTED or default not in choices):
        default = _OMITTED
    if isinstance(default, list) and default:
        default = _OMITTED
    if default is _OMITTED:
        result["default_omitted"] = "private_or_nonportable"
    else:
        result["default"] = default
    if action_kind in {"store_const", "append_const"} or nargs == "?":
        constant = _portable(action.const) if not sensitive else _OMITTED
        if isinstance(constant, str) and constant and (choices is _OMITTED or constant not in choices):
            constant = _OMITTED
        if isinstance(constant, list) and constant:
            constant = _OMITTED
        if constant is not _OMITTED:
            result["const"] = constant
        else:
            result["const_omitted"] = "private_or_nonportable"
    return result


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def cli_descriptors(parser: argparse.ArgumentParser) -> tuple[ActionDescriptor, ...]:
    descriptors: list[ActionDescriptor] = []
    parser_routes: dict[int, list[str]] = {}
    route_parsers: dict[str, int] = {}

    def visit(current: argparse.ArgumentParser, path: tuple[str, ...], inherited: list[dict[str, Any]],
              inherited_groups: list[dict[str, Any]], rules: list[dict[str, Any]], summary: str) -> None:
        arguments = inherited + [_argument(action, path) for action in current._actions if not isinstance(action, argparse._SubParsersAction)]
        groups = inherited_groups + [
            {"scope": list(path), "required": bool(group.required),
             "members": [list(action.option_strings) or [action.dest] for action in group._group_actions]}
            for group in current._mutually_exclusive_groups
        ]
        subparsers = [action for action in current._actions if isinstance(action, argparse._SubParsersAction)]
        parser_rules = rules + [{
            "scope": list(path), "allow_abbrev": current.allow_abbrev, "prefix_chars": current.prefix_chars,
            "fromfile_prefix_chars": current.fromfile_prefix_chars,
            "subcommand_required": any(action.required for action in subparsers),
        }]
        if path and callable(current.get_default("func")):
            action_id = "cli:" + " ".join(path)
            parser_routes.setdefault(id(current), []).append(action_id)
            route_parsers[action_id] = id(current)
            effects: tuple[str, ...] = ("Native handler effects have not been classified; validation may have effects.",)
            effect_status, read_only = "unknown", None
            if path in {("worker-run", "status"), ("worker-run-status",)}:
                effects = ("Native worker observation can reconcile runtime state and collect completed output.",)
                effect_status, read_only = "documented", False
            elif path in {("actions", "list"), ("actions", "describe")}:
                effects = ("Reads registration metadata and, only with exact selectors, current Work state.",)
                effect_status, read_only = "documented", True
            contract = {
                "kind": "argparse", "command_path": list(path), "arguments": arguments,
                "mutually_exclusive_groups": groups, "parser_rules": parser_rules,
                "child_commands": [name for action in subparsers for name in action.choices],
                "handler_registered": True, "invocable_without_subcommand": not any(action.required for action in subparsers),
                "native_validation_required": True,
            }
            descriptors.append(ActionDescriptor(
                action_id=action_id, surface="cli", name=" ".join(path), summary=summary or _public_text(current.description),
                contract_json=_json(contract), effect_status=effect_status, read_only=read_only, effects=effects,
                preconditions=("The native CLI parser must accept the full command path and arguments.",
                               "Command-specific current access, binding, policy and resource checks remain native obligations where applicable."),
                native_validation=("argparse conversion, choices, cardinality and mutual exclusions",
                                   "native cross-field validation, preconditions and side effects; not evaluated by discovery"),
            ))
        for subparser in subparsers:
            help_by_name = {item.dest: _public_text(item.help) for item in subparser._choices_actions}
            for name, child in subparser.choices.items():
                child_help = next((help_by_name[alias] for alias, candidate in subparser.choices.items() if candidate is child and alias in help_by_name), "")
                visit(child, path + (name,), arguments, groups, parser_rules, child_help)

    visit(parser, (), [], [], [], "")
    return tuple(replace(item, aliases=tuple(sorted(alias for alias in parser_routes[route_parsers[item.action_id]] if alias != item.action_id)))
                 for item in descriptors)


def mcp_descriptors() -> tuple[ActionDescriptor, ...]:
    # Adapter-only lazy import: registry inspection does not bootstrap Runtime.
    from pf_runtime.mcp_server import TOOLS, tool_annotations, tool_schema

    result = []
    for name, description in sorted(TOOLS.items()):
        annotations = tool_annotations(name)
        schema = tool_schema(name)
        result.append(ActionDescriptor(
            action_id="mcp:" + name, surface="mcp", name=name, summary=description,
            contract_json=_json({"kind": "mcp", "tool_name": name, "inputSchema": schema, "annotations": annotations}),
            effect_status="advertised_annotation", read_only=annotations.get("readOnlyHint"),
            effects=("Effects are declared by the advertised MCP annotations; native validation remains required.",),
            preconditions=("The advertised input schema must accept the arguments, including unknown-field rejection.",
                           "The native MCP adapter must validate applicable project/session/Work binding, intent and current access."),
            native_validation=("advertised JSON schema", "native project/session/Work binding and operation guards; not evaluated by discovery"),
        ))
    return tuple(result)


def work_facts(state: Mapping[str, Any] | None) -> WorkFacts:
    if state is None:
        return WorkFacts()

    def status(mapping: Any, key: str, allowed: set[str]) -> str:
        value = mapping.get(key) if isinstance(mapping, Mapping) else None
        return value if isinstance(value, str) and value in allowed else "unknown"

    context = state.get("context")
    validation = context.get("validation") if isinstance(context, Mapping) else None
    return WorkFacts(
        selection="explicit", context_validation=status(validation, "status", {"valid", "blocked", "invalid"}),
        execution_readiness=status(state.get("execution_readiness"), "status", {"ready", "blocked"}),
        state_action=status(state, "action", {"work_ready", "work_incomplete", "work_blocked", "work_terminal", "run_completed", "blocked", "operator_choice_required"}),
        blockers_present=bool(state.get("blockers")),
    )


def catalog_payload(
    parser_factory: Callable[[], argparse.ArgumentParser], *, operation: str, version: str,
    action_id: str = "", query: str = "", surface: str = "", limit: int = 25, offset: int = 0,
    work_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = dict(operation=operation, action_id=action_id, query=query, surface=surface, limit=limit, offset=offset)
    try:
        ActionCatalog.validate_request(**request)
    except CatalogRequestError as exc:
        return {"schema_version": 1, "kind": "pf.actions.request", "status": "blocked", "reason": exc.reason,
                **({"action_id": action_id} if isinstance(action_id, str) else {})}
    catalogue = ActionCatalog((*cli_descriptors(parser_factory()), *mcp_descriptors()), version=version,
                              sources=("running_cli_parser", "advertised_mcp_registry"))
    return catalogue.query(**request, work=work_facts(work_state))
