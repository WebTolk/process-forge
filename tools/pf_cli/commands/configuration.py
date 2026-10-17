"""Adapt existing Workplace configuration CRUD to an explicit Core factory."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from processforge_core.configuration import ConfigurationConflict, ConfigurationError

if TYPE_CHECKING:
    from processforge_core.configuration import ConfigService


class ConfigurationCommand:
    """Execute existing configuration operations with the supplied service factory."""

    def __init__(
        self,
        *,
        service_factory: Callable[[Path], ConfigService],
        project_service_factory=None,
        flow_root=None,
    ) -> None:
        self._service_factory = service_factory
        self._project_service_factory = project_service_factory
        self._flow_root = flow_root

    def execute(self, args: argparse.Namespace) -> int:
        try:
            root = Path(args.workplace).expanduser().resolve()
            if root.name == "workplace.yaml":
                root = root.parent
            service = self._service_factory(root / "configuration.yaml")
            device = None
            if getattr(args, "project_root", None):
                if self._project_service_factory is None or self._flow_root is None:
                    raise ConfigurationError("configuration_project_scope_unavailable")
                device = service.read()
                project = Path(args.project_root).expanduser().resolve()
                service = self._project_service_factory(self._flow_root(project) / "configuration.yaml")
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
            effective = snapshot.config
            if device is not None:
                effective = device.config.for_project(snapshot.config)
                payload.update(scope="project", effective_configuration=effective.to_dict())
            if args.config_command == "read" and args.key:
                payload["value"] = effective.get(args.key)
                if device is not None:
                    payload["override"] = snapshot.config.get(args.key)
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
