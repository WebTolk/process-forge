#!/usr/bin/env python3
"""Core CRUD without a host, YAML transaction failures and real CLI round trips."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from processforge_core.configuration import (
    ConfigService, ConfigSnapshot, ConfigurationConflict, ConfigurationError, PFConfig,
)
from processforge_core.configuration.yaml_store import YamlConfigStore
from processforge_platforms.file_security import native_file_security

KEY = "runtime.metrics.interval_seconds"


class MemoryStore:
    """An alternate host can supply storage without files, YAML or CLI objects."""
    def __init__(self):
        self.snapshot = ConfigSnapshot(PFConfig(), None)
        self.sequence = 0

    def read(self):
        return self.snapshot

    def write(self, config, *, expected_revision):
        if self.snapshot.revision != expected_revision:
            raise ConfigurationConflict("configuration_revision_conflict")
        self.sequence += 1
        self.snapshot = ConfigSnapshot(config, str(self.sequence))
        return self.snapshot

    def delete(self, *, expected_revision):
        assert expected_revision == self.snapshot.revision
        self.snapshot = ConfigSnapshot(PFConfig(), None)
        return self.snapshot


def rejects(call, code=None):
    try:
        call()
    except ConfigurationError as exc:
        if code:
            assert exc.code == code, exc.code
    else:
        raise AssertionError("invalid operation was accepted")


def cli(root, command, *args, exit_code=0):
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/processforge.py"),
                             "config", command, "--workplace", str(root), "--json", *args],
                            capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == exit_code, (result.stdout, result.stderr)
    assert result.stderr == "" and "\x1b" not in result.stdout
    return json.loads(result.stdout)


def main():
    memory = ConfigService(MemoryStore())
    assert not memory.read().exists
    memory.create()
    rejects(memory.create, "configuration_revision_conflict")
    memory.update({KEY: 1})
    assert memory.read().config.get(KEY) == 1
    assert memory.reset(KEY).config.get(KEY) == 10
    assert not memory.delete().exists
    original = PFConfig()
    changed = original.with_changes({KEY: 2})
    assert original.get(KEY) == 10 and changed.get(KEY) == 2
    try:
        changed.runtime.metrics.interval_seconds = 3
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("configuration must be immutable")
    for value in (True, "2", None, [], {}, 0, 61, float("nan"), float("inf")):
        rejects(lambda: original.with_changes({KEY: value}))
    for value in (None, [], {"unknown": 1}, {"runtime": None}, {"schema_version": True}, {"schema_version": 2}):
        rejects(lambda: PFConfig.from_dict(value))
    for key in (None, "", "unknown", "runtime.metrics.nope"):
        rejects(lambda: original.get(key))
    validator = runpy.run_path(str(ROOT / "tools/validate-process-forge-schemas.py"))["validate_instance"]
    schema = json.loads((ROOT / "schemas/workplace-configuration.schema.json").read_text())
    for value, valid in (({}, True), (original.to_dict(), True), ({"runtime": {"metrics": {"interval_seconds": 61}}}, False), ({"runtime": {"metrics": {"interval_seconds": True}}}, False), ({"unknown": 1}, False)):
        assert bool(validator(value, schema, schema, "$")) != valid

    with tempfile.TemporaryDirectory(prefix="pf-config-") as temp:
        root = Path(temp).resolve()
        path = root / "configuration.yaml"
        store = YamlConfigStore(path)
        service = ConfigService(store)
        assert not service.read().exists and list(root.iterdir()) == []
        snapshot = service.create()
        rejects(service.create, "configuration_revision_conflict")
        before = path.read_bytes()
        for value in (True, -1, 61, "2", float("nan")):
            rejects(lambda: service.update({KEY: value}))
            assert path.read_bytes() == before
        security = native_file_security()
        permissions = security.fingerprint(path)
        latest = service.update({KEY: 1}, expected_revision=snapshot.revision)
        assert security.fingerprint(path) == permissions
        rejects(lambda: service.update({KEY: 2}, expected_revision=snapshot.revision), "configuration_revision_conflict")
        # Two independent readers: the storage CAS rejects the second write.
        other = YamlConfigStore(path)
        stale = other.read()
        service.update({KEY: 2})
        rejects(lambda: other.write(stale.config, expected_revision=stale.revision), "configuration_revision_conflict")
        before = path.read_bytes()
        with patch("os.replace", side_effect=OSError("private storage error")):
            rejects(lambda: service.update({KEY: 3}), "configuration_write_failed")
        assert path.read_bytes() == before and not list(root.glob(".configuration-*.tmp"))
        with store._lock():
            busy = cli(root, "update", "--key", KEY, "--value", "3", exit_code=3)
            assert busy["error"] == "configuration_writer_busy"
        assert path.read_bytes() == before
        for raw in (b"", b"[", b"runtime: {}\nruntime: {}", b"runtime: &a {}", b"runtime: *a", b"runtime: !!python/object:x {}", b"\xff", b"x" * 65537):
            path.write_bytes(raw)
            rejects(service.read)
            rejects(lambda: service.update({KEY: 2}))
            assert path.read_bytes() == raw
        path.write_bytes(before)
        assert service.reset(KEY).config.get(KEY) == 10
        assert not service.delete().exists
        assert not service.read().exists
        rejects(lambda: service.update({KEY: 2}), "configuration_missing")
        missing = root / "absent"
        assert not cli(missing, "read")["exists"] and not missing.exists()
        assert cli(missing, "create", exit_code=1)["error"] == "configuration_write_failed"
        current = cli(root, "create")
        assert cli(root, "read", "--key", KEY)["value"] == 10
        newer = cli(root / "workplace.yaml", "update", "--key", KEY, "--value", "2", "--if-revision", current["revision"])
        assert newer["configuration"]["runtime"]["metrics"]["interval_seconds"] == 2
        assert cli(root, "delete", "--if-revision", current["revision"], exit_code=3)["error"] == "configuration_revision_conflict"
        assert cli(root, "update", "--key", "schema_version", "--value", "1", exit_code=1)["error"] == "configuration_key_unknown"
        assert cli(root, "delete", "--key", KEY)["configuration"]["runtime"]["metrics"]["interval_seconds"] == 10
        assert not cli(root, "delete")["exists"]
        assert set(p.name for p in root.iterdir()) == {"configuration.yaml.lock"}
        # Optional configuration is produced for newly generated workplaces.
        import processforge as core
        generated = core.build_workplace_files(root, {})
        assert YamlConfigStore._decode(generated[path].encode("utf-8")) == PFConfig()
        template = (ROOT / "templates/workplace-configuration.yaml").read_bytes()
        assert YamlConfigStore._decode(template) == PFConfig()
        # Doctor validates the same model for present/absent/invalid settings.
        fixture = root / "generated"
        for target, content in core.build_workplace_files(fixture, {}).items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for raw, expected in ((template, "configuration.yaml valid"), (None, "configuration.yaml absent; defaults apply"), (b"runtime: [", "configuration_yaml_invalid")):
            config_path = fixture / "configuration.yaml"
            if raw is None:
                config_path.unlink()
            else:
                config_path.write_bytes(raw)
            with patch.object(core, "print_checks", return_value=0) as report:
                core.command_doctor_workplace(argparse.Namespace(root=str(fixture)))
            checks = report.call_args.args[0]
            assert any(item.message == expected and item.level == ("FAIL" if raw == b"runtime: [" else "PASS") for item in checks)
        independent = ConfigService(YamlConfigStore(root / "other.yaml"))
        independent.create(PFConfig().with_changes({KEY: 2}))
        assert service.read().config.get(KEY) == 10 and independent.read().config.get(KEY) == 2
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        with patch.object(core.diagnostics, "for_project", side_effect=AssertionError("config read attempted diagnostic writes")), redirect_stdout(io.StringIO()) as output:
            assert core.main(["--diagnostic-profile", "trace", "--diagnostic-sink", "both", "config", "read", "--workplace", str(root), "--json"]) == 0
            assert not json.loads(output.getvalue())["exists"]
        assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    print("PASS: independent immutable Core CRUD, defaults/validation, revisions, locking, atomic failure, permissions, YAML bounds and CLI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
