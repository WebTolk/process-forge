#!/usr/bin/env python3
"""Capability record behavior, isolated Core imports, and real consumer failures.

Consumer probes control registry/source discovery and stop at a provider failure.
They complement the normal Work capsule and context-readiness integration smokes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import importlib.abc
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]



def raises(kind, message, call):
    try:
        call()
    except kind as exc:
        if message is not None:
            assert str(exc) == message, (type(exc).__name__, str(exc), message)
    else:
        raise AssertionError('expected ' + kind.__name__ + ': ' + str(message))


def check_capabilities(capabilities):
    checks = []
    marker = {'provider': 'same object'}
    providers = {'none': None, 'false': False, 'zero': 0, 'empty': '', 'list': [], 'object': marker}
    required = ['object', 'missing', 'object', 'none', 'false', 'zero', 'empty', 'list']
    optional = ['missing', 'object', 'missing']
    records = capabilities(required, optional, providers)
    assert isinstance(records, tuple) and len(records) == 2
    assert [row['id'] for row in records[0]] == required
    assert [row['id'] for row in records[1]] == optional
    assert records[0][0] is not records[0][2]
    for group, severity in zip(records, ['fail', 'warn']):
        for row in group:
            assert list(row) == ['id', 'status', 'provider', 'severity']
            if row['id'] == 'missing':
                assert row == {'id': 'missing', 'status': 'missing', 'provider': None, 'severity': severity}
            else:
                assert row['status'] == 'available' and row['severity'] == 'info'
                assert row['provider'] is providers[row['id']]
    assert required == ['object', 'missing', 'object', 'none', 'false', 'zero', 'empty', 'list']
    assert optional == ['missing', 'object', 'missing']
    checks.append('order_duplicates_key_order_falsey_and_provider_identity')

    events = []

    class Items:
        def __init__(self, phase, items):
            self.phase, self.items = phase, items

        def __iter__(self):
            events.append(self.phase + ':iter')
            for item in self.items:
                events.append(self.phase + ':' + item)
                yield item

    class Providers(dict):
        def __iter__(self):
            events.append('providers:iter')
            return super().__iter__()

        def get(self, key):
            events.append('get:' + key)
            return marker

    rows = capabilities(Items('required', ['absent', 'present', 'absent']),
                        Items('optional', ['absent', 'present']), Providers(present=marker))
    assert events == ['providers:iter', 'required:iter', 'required:absent', 'get:absent',
                      'required:present', 'get:present', 'required:absent', 'get:absent',
                      'optional:iter', 'optional:absent', 'get:absent', 'optional:present', 'get:present'], events
    assert rows[0][0]['provider'] is None and rows[1][0]['provider'] is None
    assert rows[0][1]['provider'] is marker and rows[1][1]['provider'] is marker
    checks.append('unconditional_custom_dict_get_and_required_before_optional')

    class HashKey:
        def __hash__(self):
            events.append('membership:hash')
            return 77

    key = HashKey()

    class MembershipProviders(dict):
        def get(self, value):
            assert value is key
            events.append('providers:get')
            return marker

    events.clear()
    row = capabilities([key], [], MembershipProviders())[0][0]
    assert events == ['membership:hash', 'providers:get'], events
    assert row['id'] is key and row['provider'] is None and row['status'] == 'missing'
    checks.append('membership_before_get_and_capability_identity')

    class MutatingProviders(dict):
        def get(self, key):
            if key == 'first':
                self.pop('gone')
                self['late'] = marker
            return super().get(key)

    changing = MutatingProviders(first=marker, gone=marker)
    rows = capabilities(['first', 'gone', 'late'], ['gone', 'late'], changing)
    assert [row['status'] for row in rows[0]] == ['available', 'available', 'missing']
    assert [row['status'] for row in rows[1]] == ['available', 'missing']
    assert rows[0][1]['provider'] is None and rows[1][0]['provider'] is None
    assert rows[0][2]['provider'] is None and rows[1][1]['provider'] is None
    checks.append('availability_snapshot_survives_provider_mutation')

    class IterFailure(dict):
        def __iter__(self):
            raise RuntimeError('provider iteration first')

    raises(RuntimeError, 'provider iteration first', lambda: capabilities(None, None, IterFailure()))
    raises(RuntimeError, 'provider iteration first', lambda: capabilities([], [], IterFailure()))
    checks.append('provider_iteration_even_empty_and_error_precedence')

    events.clear()

    class GetFailure(dict):
        def get(self, key):
            events.append('get:' + key)
            raise ValueError('missing get still called')

    raises(ValueError, 'missing get still called',
           lambda: capabilities(['absent'], Items('optional', ['unused']), GetFailure()))
    assert events == ['get:absent'], events
    events.clear()
    raises(TypeError, None, lambda: capabilities([[]], [], GetFailure()))
    assert events == [], events
    checks.append('missing_get_errors_and_unhashable_membership_before_get')

    class RequiredFailure:
        def __iter__(self):
            events.append('required:iter')
            yield 'ok'
            raise LookupError('required iteration failed')

    events.clear()
    raises(LookupError, 'required iteration failed',
           lambda: capabilities(RequiredFailure(), Items('optional', ['unused']), Providers(ok=marker)))
    assert events == ['providers:iter', 'required:iter', 'get:ok'], events
    events.clear()
    raises(TypeError, "'NoneType' object is not iterable", lambda: capabilities(None, Items('optional', []), Providers()))
    assert events == ['providers:iter'], events
    events.clear()
    raises(TypeError, "'NoneType' object is not iterable", lambda: capabilities(Items('required', ['ok']), None, Providers(ok=marker)))
    assert events == ['providers:iter', 'required:iter', 'required:ok', 'get:ok'], events
    checks.append('required_failure_suppresses_optional_and_optional_failure_follows_required')
    assert capabilities([], [], {}) == ([], [])
    checks.append('empty_result')
    return checks


class NoTransportImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname in {"processforge", "processforge_core._legacy_processforge"}
                or fullname.split(".")[0] in {"tools", "pf_cli", "pf_runtime"}):
            raise AssertionError("Core attempted a monolith or transport import: " + fullname)
        return None


def core_only(src):
    sys.path.insert(0, str(src))
    guard = NoTransportImports()
    sys.meta_path.insert(0, guard)
    try:
        from processforge_core.project.readiness import ProjectContextReadinessPolicy
        owner = ProjectContextReadinessPolicy()
        assert Path(sys.modules[ProjectContextReadinessPolicy.__module__].__file__).resolve().is_relative_to(src.resolve())
        checks = check_capabilities(owner.capabilities)
        assert "processforge" not in sys.modules
        assert "processforge_core._legacy_processforge" not in sys.modules
        assert not any(name.split(".")[0] in {"pf_cli", "pf_runtime"} for name in sys.modules)
        return checks
    finally:
        sys.meta_path.remove(guard)


def consumer_failures(scratch):
    # Load the real source facade only after the independent Core import checks.
    # No Runtime, MCP, registration, Work start, or capsule write is performed.
    sys.path.insert(0, str(ROOT / "tools"))
    import processforge as core
    from processforge_core.work import context as work_context
    from processforge_core.project.capability_registry import CapabilityRegistryReader

    project = scratch / "consumer-fixture"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    (flow / "process-forge.yaml").write_text("project:\n  id: capability-probe\nrequired_capabilities: [required]\noptional_capabilities: [optional]\n", encoding="utf8")
    snapshot_path = flow / "contexts/project-context.snapshot.yaml"
    snapshot_path.parent.mkdir()
    snapshot_path.write_text("snapshot:\n  id: capability-probe\n", encoding="utf8")
    assignment = flow / "assignments/probe.yaml"
    assignment.parent.mkdir()
    metadata = {"id": "probe", "required_capabilities": ["required"], "optional_capabilities": ["optional"]}
    snapshot = {"snapshot": {"id": "capability-probe"}}
    events = []

    class ProviderFailure(ValueError):
        pass

    class Providers(dict):
        def get(self, key):
            events.append(key)
            raise ProviderFailure("capability provider failure")

    # Leave the actual default readiness owner untouched. A forbidden legacy
    # helper catches a reverse route even if someone recreates the old adapter.
    def forbidden_reverse(*args, **kwargs):
        raise AssertionError("consumer called the old capability helper")

    checks = []
    with ExitStack() as stack:
        stack.enter_context(patch.object(core, "capability_records", forbidden_reverse, create=True))
        stack.enter_context(patch.object(CapabilityRegistryReader, "read", return_value=Providers()))
        from processforge_core.project.coordination_state import ProjectCoordinationStateService

        stack.enter_context(patch.object(ProjectCoordinationStateService, "resolve_project_workplace_manifest", return_value=None))
        stack.enter_context(patch.object(core._ProjectSnapshotSourcesReader, "read", return_value=[]))
        raises(ProviderFailure, "capability provider failure", lambda: core.build_project_context_snapshot(project))
        assert events == ["required"], events
        checks.append("build_project_context_snapshot_real_failure_path")
        events.clear()
        stack.enter_context(patch.object(core, "extract_assignment_front_matter", return_value=metadata))
        stack.enter_context(patch.object(core, "project_context_freshness", return_value=("fresh", [], snapshot)))
        args = argparse.Namespace(project_root=str(project), assignment=str(assignment), force=False)
        raises(ProviderFailure, "capability provider failure", lambda: core.command_assignment_capsule(args))
        assert events == ["required"], events
        checks.append("command_assignment_capsule_real_failure_path")
        events.clear()
        # Real normalization and intent compilation run before the owner. Empty
        # resource selection avoids unrelated knowledge lookup in this probe.
        pin = {"snapshot_id": "capability-probe", "snapshot_checksum": "sha256:" + core.sha256_file(snapshot_path)}
        raises(ProviderFailure, "capability provider failure",
               lambda: work_context.build_context_fields(project, assignment, metadata, snapshot, core, pin=pin, run_record={}))
        assert events == ["required"], events
        checks.append("build_context_fields_real_failure_path_without_reverse_helper")
    assert not (flow / "contexts/assignment-capsules/probe.capsule.yaml").exists()
    return checks


def run(scratch):
    checks = core_only(ROOT / "src")
    copied = scratch / "copied-core"
    shutil.copytree(ROOT / "src", copied / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    probe = copied / "probe.py"
    probe.write_text(Path(__file__).read_text(encoding="utf8"), encoding="utf8")
    assert not (copied / "tools").exists()
    result = subprocess.run([sys.executable, "-I", "-B", str(probe), "--core-only", str(copied / "src")],
                            cwd=copied, capture_output=True, text=True, encoding="utf8", timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "PASS: isolated Core capability records" in result.stdout
    checks.append("copied_src_isolated_python_default_owner_without_monolith_or_transport")
    checks.extend(consumer_failures(scratch))
    for check in checks:
        print("PASS: " + check)
    print("PASS: project context capability records real Core smoke")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, help="Existing parent for disposable test files.")
    parser.add_argument("--core-only", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.core_only:
        core_only(args.core_only)
        print("PASS: isolated Core capability records")
        return
    if args.scratch:
        scratch = args.scratch.resolve() / ("pf-capability-records-" + uuid.uuid4().hex)
        scratch.mkdir()
        try:
            run(scratch)
        finally:
            shutil.rmtree(scratch)
    else:
        with tempfile.TemporaryDirectory(prefix="pf-capability-records-") as raw:
            run(Path(raw))


if __name__ == "__main__":
    main()
