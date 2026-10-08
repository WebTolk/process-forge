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
