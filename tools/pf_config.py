"""CLI adapter for the interface-independent configuration service."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from processforge_core.configuration import ConfigService, ConfigurationConflict, ConfigurationError
from processforge_core.configuration.yaml_store import YamlConfigStore


def command_config(args) -> int:
    try:
        root = Path(args.workplace).expanduser().resolve()
        if root.name == "workplace.yaml":
            root = root.parent
        service = ConfigService(YamlConfigStore(root / "configuration.yaml"))
        if args.config_command == "create":
            snapshot = service.create()
        elif args.config_command == "update":
            try:
                value = json.loads(args.value)
            except ValueError:
                raise ConfigurationError("configuration_value_requires_json") from None
            snapshot = service.update({args.key: value}, expected_revision=args.if_revision)
        elif args.config_command == "delete":
            snapshot = (service.reset(args.key, expected_revision=args.if_revision) if args.key
                        else service.delete(expected_revision=args.if_revision))
        else:
            snapshot = service.read()
        payload = {"kind": "pf.configuration", "exists": snapshot.exists, "revision": snapshot.revision,
                   "configuration": snapshot.config.to_dict()}
        if args.config_command == "read" and args.key:
            payload["value"] = snapshot.config.get(args.key)
        print(json.dumps(payload, ensure_ascii=True, indent=None if args.json else 2, sort_keys=True))
        return 0
    except ConfigurationError as exc:
        payload = {"kind": "pf.configuration", "error": exc.code}
        print(json.dumps(payload), file=sys.stdout if args.json else sys.stderr)
        return 3 if isinstance(exc, ConfigurationConflict) else 1
    except (OSError, RuntimeError, ValueError):
        print(json.dumps({"kind": "pf.configuration", "error": "configuration_path_invalid"}),
              file=sys.stdout if args.json else sys.stderr)
        return 1


def register(subparsers) -> None:
    parser = subparsers.add_parser("config", help="Manage the selected workplace configuration through Core CRUD.")
    commands = parser.add_subparsers(dest="config_command", required=True)
    for name in ("create", "read", "update", "delete"):
        command = commands.add_parser(name)
        command.add_argument("--workplace", required=True, help="Workplace directory or workplace.yaml.")
        command.add_argument("--json", action="store_true", help="Return one JSON object.")
        if name in {"read", "update", "delete"}:
            command.add_argument("--key", required=name == "update", help="Dotted setting name; delete with a key resets it to its default.")
        if name == "update":
            command.add_argument("--value", required=True, help="New value as JSON, for example 2.")
        if name in {"update", "delete"}:
            command.add_argument("--if-revision", help="Reject a stale client revision returned by read.")
        command.set_defaults(func=command_config)
