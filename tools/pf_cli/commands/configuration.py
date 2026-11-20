"""Adapt existing Workplace configuration CRUD to an explicit Core factory."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from processforge_core.composition import build_configuration_provider
from processforge_core.configuration import (
    ConfigurationConflict,
    ConfigurationError,
    ConfigurationProvider,
    DeviceConfigurationSource,
)

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
        device_config_path: Path | None = None,
        configuration_factory: Callable[
            ..., ConfigurationProvider
        ] = build_configuration_provider,
    ) -> None:
        self._service_factory = service_factory
        self._project_service_factory = project_service_factory
        self._flow_root = flow_root
        self._device_config_path = device_config_path
        self._configuration_factory = configuration_factory

    def execute(self, args: argparse.Namespace) -> int:
        try:
            device_scope = bool(getattr(args, "device", False))
            project_ref = getattr(args, "project_root", None)
            if device_scope and project_ref:
                raise ConfigurationError("configuration_scope_invalid")
            provider = None
            effective_snapshot = None
            if device_scope:
                path = (
                    self._device_config_path
                    if self._device_config_path is not None
                    else DeviceConfigurationSource.default_path()
                )
                service = self._service_factory(path)
            else:
                root = Path(args.workplace).expanduser().resolve()
                if root.name == "workplace.yaml":
                    root = root.parent
                service = self._service_factory(root / "configuration.yaml")
                if project_ref:
                    if self._project_service_factory is None or self._flow_root is None:
                        raise ConfigurationError(
                            "configuration_project_scope_unavailable"
                        )
                    project = Path(project_ref).expanduser().resolve()
                    provider = self._configuration_factory(
                        device_config_path=self._device_config_path,
                        workplace_root=root,
                        project_root=project,
                    )
                    # Validate selected sources before a project mutation. Reads use this snapshot once.
                    effective_snapshot = provider.snapshot()
                    service = self._project_service_factory(
                        self._flow_root(project) / "configuration.yaml"
                    )
            if args.config_command == "create":
                if device_scope:
                    # Only explicit device creation owns its optional directory.
                    if not path.is_absolute():
                        raise ConfigurationError("configuration_absolute_path_required")
                    if path.parent.resolve() != path.parent:
                        raise ConfigurationError("configuration_unsafe_path")
                    path.parent.mkdir(parents=True, exist_ok=True)
                snapshot = service.create()
            elif args.config_command == "update":
                try:
                    value = json.loads(args.value)
                except ValueError:
                    raise ConfigurationError(
                        "configuration_value_requires_json"
                    ) from None
                snapshot = service.update(
                    {args.key: value}, expected_revision=args.if_revision
                )
            elif args.config_command == "delete":
                snapshot = (
                    service.reset(args.key, expected_revision=args.if_revision)
                    if args.key
                    else service.delete(expected_revision=args.if_revision)
                )
            else:
                snapshot = (
                    effective_snapshot.project
                    if effective_snapshot is not None
                    else service.read()
                )
            payload = {
                "kind": "pf.configuration",
                "exists": snapshot.exists,
                "revision": snapshot.revision,
                "configuration": snapshot.config.to_dict(),
            }
            effective = snapshot.config
            if device_scope:
                payload["scope"] = "device"
            if provider is not None:
                if args.config_command != "read":
                    effective_snapshot = provider.snapshot(refresh=True)
                assert effective_snapshot is not None
                effective = effective_snapshot.config
                payload.update(
                    scope="project", effective_configuration=effective.to_dict()
                )
            if args.config_command == "read" and args.key:
                payload["value"] = effective.get(args.key)
                if provider is not None:
                    payload["override"] = snapshot.config.get(args.key)
            print(
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    indent=None if args.json else 2,
                    sort_keys=True,
                )
            )
            return 0
        except ConfigurationError as exc:
            payload = {"kind": "pf.configuration", "error": exc.code}
            print(json.dumps(payload), file=sys.stdout if args.json else sys.stderr)
            return 3 if isinstance(exc, ConfigurationConflict) else 1
        except (OSError, RuntimeError, ValueError):
            print(
                json.dumps(
                    {"kind": "pf.configuration", "error": "configuration_path_invalid"}
                ),
                file=sys.stdout if args.json else sys.stderr,
            )
            return 1
