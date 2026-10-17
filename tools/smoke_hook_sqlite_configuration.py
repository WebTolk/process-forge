#!/usr/bin/env python3
"""Two independent logging flags, device/project inheritance and live resolution."""
from __future__ import annotations

from itertools import product
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core.configuration import ConfigService, PFConfig, ProjectPFConfig, ConfigurationError
from processforge_core.configuration.resolution import ConfigurationResolver
from processforge_core.configuration.yaml_store import YamlConfigStore
from processforge_core.process_event_journal import ProcessEventJournal
from smoke_workplace_configuration import cli


def main():
    with tempfile.TemporaryDirectory(prefix="pf-logging-config-") as directory:
        root = Path(directory)
        device, project = root / "configuration.yaml", root / "project/.pf/configuration.yaml"
        resolver = ConfigurationResolver()
        assert resolver.resolve(device, project).config == PFConfig()
        assert not device.exists() and not project.exists()
        project.parent.mkdir(parents=True)
        for global_raw, global_events, override_raw, override_events in product((False, True), (False, True), (None, False, True), (None, False, True)):
            global_config = PFConfig.from_dict({"logging": {"raw_hooks": global_raw, "events": global_events}})
            overrides = ProjectPFConfig.from_dict({"logging": {"raw_hooks": override_raw, "events": override_events}})
            effective = global_config.for_project(overrides).logging
            assert effective.raw_hooks == (global_raw if override_raw is None else override_raw)
            assert effective.events == (global_events if override_events is None else override_events)
        global_service = ConfigService(YamlConfigStore(device))
        project_service = ConfigService(YamlConfigStore(project, model=ProjectPFConfig), defaults=ProjectPFConfig())
        global_service.create()
        project_service.create()
        global_service.update({"logging.events": False, "logging.raw_hooks": False})
        assert not resolver.resolve(device, project).config.logging.events
        project_service.update({"logging.events": True})
        assert resolver.resolve(device, project).config.logging.events
        assert not resolver.resolve(device, project).config.logging.raw_hooks
        # An unchanged hook does not reparse configuration YAML.
        with patch.object(YamlConfigStore, "read", side_effect=AssertionError("warm YAML read")):
            assert resolver.resolve(device, project).config.logging.events
        project_service.reset("logging.events")
        assert not resolver.resolve(device, project).config.logging.events
        project_service.update({"logging.events": True})
        resolver.resolve(device, project)
        project.write_text("logging: {events: invalid}\n", encoding="utf-8")
        last_good = resolver.resolve(device, project)
        assert last_good.errors and last_good.config.logging.events
        try:
            ConfigurationResolver().resolve(device, project)
        except ConfigurationError:
            pass
        else:
            raise AssertionError("invalid first configuration silently accepted")
        project.unlink()
        assert not resolver.resolve(device, project).config.logging.events
        global_service.delete()
        assert resolver.resolve(device, project).config.logging.events
        # Project CLI read returns effective value plus the nullable override.
        target = root / "project"
        cli(root, "create", "--project-root", str(target))
        payload = cli(root, "update", "--project-root", str(target), "--key", "logging.raw_hooks", "--value", "false")
        assert payload["effective_configuration"]["logging"]["raw_hooks"] is False
        assert cli(root, "read", "--project-root", str(target), "--key", "logging.events")["override"] is None
        cli(root, "delete", "--project-root", str(target), "--key", "logging.raw_hooks")
        assert cli(root, "read", "--project-root", str(target), "--key", "logging.raw_hooks")["value"] is True
        # Latest verification is required working state, independent of history.
        journal, path = ProcessEventJournal(), root / "events.sqlite3"
        for subject in ("task-1", "task-2"):
            journal.append(path, {"event_id": subject, "event_type": "passed", "subject": subject,
                                  "data": {"verification_fingerprint": subject}}, record=False)
        assert journal.count(path) == 0
        assert journal.latest_assignment_event(path, "task-1", {"passed"})["event_id"] == "task-1"
        assert journal.latest_assignment_event(path, "task-2", {"passed"})["event_id"] == "task-2"
    print("PASS: 36 inheritance combinations, independent flags, live CRUD/reload, last-valid errors and verification without history")


if __name__ == "__main__":
    main()
